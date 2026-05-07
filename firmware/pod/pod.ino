/*
 * EcoAdapt Pod Firmware
 * Target: Seeed XIAO ESP32-C3
 *
 * Role: Sensor pod inside plant pot. Battery-powered (1200mAh LiPo).
 * Reads soil moisture, temperature, light. Sends to bridge via ESP-NOW.
 * Sleeps between readings to maximize battery life.
 *
 * Hardware:
 *   - HW-390 capacitive moisture sensor → D2 (GPIO4) direct analog
 *   - VEML7700 lux sensor (I2C: SDA=GPIO6, SCL=GPIO7)
 *   - DS18B20 temperature probe → D3 (GPIO5), 4.7kΩ pullup to 3.3V
 *
 * NVS keys (preferences namespace "ecoadapt"):
 *   read_interval     uint32  seconds between sensor reads (default 300)
 *   check_interval    uint32  seconds between command checks (default 30)
 *   mode              string  "DEMO" | "NORMAL" | "ECO"
 *   sleep_indefinite  bool    if true, do not auto-wake
 *   bridge_mac        bytes   6-byte MAC of the bridge
 *   pod_id            string  short identifier echoed in packets
 */

#include <Arduino.h>
#include <Wire.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <WiFi.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <Adafruit_VEML7700.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <esp_sleep.h>

// ---------- Pin map (XIAO ESP32-C3) ----------
#define PIN_MOISTURE       4    // D2 = GPIO4, ADC1 direct analog
#define PIN_ONEWIRE        5    // D3 = GPIO5, DS18B20 1-Wire
#define PIN_LED_STATUS     8    // built-in LED (active low)

// Moisture calibration (capacitive, 12-bit ADC)
#define MOISTURE_DRY_RAW   3771  // probe in air
#define MOISTURE_WET_RAW   1884  // probe submerged

// I2C: SDA=GPIO6, SCL=GPIO7 (XIAO C3 default)

// ---------- Defaults ----------
static const uint32_t DEFAULT_READ_INTERVAL_S  = 300;
static const uint32_t DEFAULT_CHECK_INTERVAL_S = 30;
static const char*    DEFAULT_MODE             = "NORMAL";

// ---------- RTC memory ----------
RTC_DATA_ATTR int      bootCount  = 0;
RTC_DATA_ATTR bool     firstBoot  = true;

// ---------- Globals ----------
Preferences       prefs;
Adafruit_VEML7700 veml;
OneWire           oneWire(PIN_ONEWIRE);
DallasTemperature ds18b20(&oneWire);

bool vemlOk = false;
bool dsOk   = false;

uint8_t bridgeMac[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
String  podId        = "pod-default";
String  currentMode  = DEFAULT_MODE;

uint32_t readIntervalS   = DEFAULT_READ_INTERVAL_S;
uint32_t checkIntervalS  = DEFAULT_CHECK_INTERVAL_S;
bool     sleepIndefinite = false;

volatile bool ackReceived     = false;
volatile bool commandReceived = false;
char          pendingCommand[256] = {0};

// =================== UTIL ===================
void blink(int times, int ms = 80) {
  pinMode(PIN_LED_STATUS, OUTPUT);
  for (int i = 0; i < times; i++) {
    digitalWrite(PIN_LED_STATUS, LOW);   // active low
    delay(ms);
    digitalWrite(PIN_LED_STATUS, HIGH);
    delay(ms);
  }
}

float readBatteryVoltage() {
  return -1.0f; // not wired
}

// =================== NVS ===================
void loadConfig() {
  prefs.begin("ecoadapt", true);
  readIntervalS   = prefs.getUInt("read_interval",  DEFAULT_READ_INTERVAL_S);
  checkIntervalS  = prefs.getUInt("check_interval", DEFAULT_CHECK_INTERVAL_S);
  currentMode     = prefs.getString("mode",         DEFAULT_MODE);
  sleepIndefinite = prefs.getBool("sleep_indef",    false);
  podId           = prefs.getString("pod_id",       "pod-default");
  size_t macLen   = prefs.getBytesLength("bridge_mac");
  if (macLen == 6) prefs.getBytes("bridge_mac", bridgeMac, 6);
  prefs.end();

  Serial.printf("[CFG] mode=%s read=%us check=%us pod_id=%s\n",
    currentMode.c_str(), readIntervalS, checkIntervalS, podId.c_str());
  Serial.printf("[CFG] bridge_mac=%02X:%02X:%02X:%02X:%02X:%02X\n",
    bridgeMac[0],bridgeMac[1],bridgeMac[2],
    bridgeMac[3],bridgeMac[4],bridgeMac[5]);
}

void saveMode(const String& m) {
  prefs.begin("ecoadapt", false);
  prefs.putString("mode", m);
  if      (m == "DEMO")   { prefs.putUInt("read_interval", 60);   prefs.putUInt("check_interval", 10); }
  else if (m == "NORMAL") { prefs.putUInt("read_interval", 300);  prefs.putUInt("check_interval", 30); }
  else if (m == "ECO")    { prefs.putUInt("read_interval", 1800); prefs.putUInt("check_interval", 300); }
  prefs.end();
}

void saveBridgeMac(const uint8_t* mac) {
  prefs.begin("ecoadapt", false);
  prefs.putBytes("bridge_mac", mac, 6);
  prefs.end();
  memcpy(bridgeMac, mac, 6);
}

void resetConfig() {
  prefs.begin("ecoadapt", false);
  prefs.clear();
  prefs.end();
}

// =================== SENSORS ===================
void initSensors() {
  Wire.begin(6, 7);

  // VEML7700
  if (veml.begin()) {
    vemlOk = true;
    veml.setGain(VEML7700_GAIN_1);
    veml.setIntegrationTime(VEML7700_IT_100MS);
    Serial.println("[SENS] VEML7700 OK");
  } else {
    Serial.println("[SENS] VEML7700 FAIL");
  }

  // DS18B20
  ds18b20.begin();
  if (ds18b20.getDeviceCount() > 0) {
    dsOk = true;
    Serial.println("[SENS] DS18B20 OK");
  } else {
    Serial.println("[SENS] DS18B20 FAIL");
  }
}

int readMoisturePercent() {
  // Average 10 samples to reduce ESP32 ADC noise
  long sum = 0;
  for (int i = 0; i < 10; i++) { sum += analogRead(PIN_MOISTURE); delay(5); }
  int raw = sum / 10;
  return constrain(map(raw, MOISTURE_DRY_RAW, MOISTURE_WET_RAW, 0, 100), 0, 100);
}

float readLux() {
  if (!vemlOk) return -1.0f;
  return veml.readLux();
}

float readTempC() {
  if (!dsOk) return -1000.0f;
  // Retry up to 3 times — voltage sag during ESP-NOW can drop 1-Wire signal
  float t = DEVICE_DISCONNECTED_C;
  for (int attempt = 0; attempt < 3 && t == DEVICE_DISCONNECTED_C; attempt++) {
    if (attempt > 0) { delay(100); ds18b20.begin(); }
    ds18b20.requestTemperatures();
    delay(750);
    t = ds18b20.getTempCByIndex(0);
  }
  return (t == DEVICE_DISCONNECTED_C) ? -1000.0f : t;
}

// =================== ESP-NOW ===================
typedef struct __attribute__((packed)) {
  char     type[8];
  char     pod_id[24];
  uint32_t timestamp;
  int      moisture_pct;
  float    temp_c;
  float    lux;
  float    battery_v;
  uint8_t  boot_count;
} ReadingPacket;

typedef struct __attribute__((packed)) {
  char type[8];
  char payload[200];
} CommandPacket;

void onDataSent(const wifi_tx_info_t* info, esp_now_send_status_t status) {
  ackReceived = (status == ESP_NOW_SEND_SUCCESS);
  Serial.printf("[ESPNOW] send status=%d\n", status);
}

void onDataRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  if (len < 4) return;
  if (len >= (int)sizeof(CommandPacket) - 8 && memcmp(data, "CMD", 3) == 0) {
    CommandPacket cmd;
    memset(&cmd, 0, sizeof(cmd));
    memcpy(&cmd, data, min((int)sizeof(cmd), len));
    strncpy(pendingCommand, cmd.payload, sizeof(pendingCommand) - 1);
    commandReceived = true;
    Serial.printf("[ESPNOW] CMD: %s\n", pendingCommand);
    if (bridgeMac[0] == 0xFF) saveBridgeMac(info->src_addr);
  } else if (len >= 4 && memcmp(data, "PAIR", 4) == 0) {
    saveBridgeMac(info->src_addr);
    Serial.println("[ESPNOW] paired with bridge");
  }
}

bool initEspNow() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  if (esp_now_init() != ESP_OK) {
    Serial.println("[ESPNOW] init FAIL");
    return false;
  }
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataRecv);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, bridgeMac, 6);
  peer.channel = 0;
  peer.encrypt = false;
  if (!esp_now_is_peer_exist(bridgeMac)) {
    if (esp_now_add_peer(&peer) != ESP_OK) {
      Serial.println("[ESPNOW] add_peer FAIL");
      return false;
    }
  }
  return true;
}

bool sendReading() {
  // Read sensors BEFORE transmitting — ESP-NOW radio causes voltage sag
  // that can drop the 1-Wire bus if we read after
  int   moisture = readMoisturePercent();
  float tempC    = readTempC();
  float lux      = readLux();

  ReadingPacket p = {};
  strncpy(p.type,   "READING",      sizeof(p.type)-1);
  strncpy(p.pod_id, podId.c_str(),  sizeof(p.pod_id)-1);
  p.timestamp    = millis();
  p.moisture_pct = moisture;
  p.temp_c       = tempC;
  p.lux          = lux;
  p.battery_v    = readBatteryVoltage();
  p.boot_count   = (uint8_t)(bootCount & 0xFF);

  Serial.printf("[READ] m=%d%% t=%.1fC lux=%.1f boot=%d\n",
    p.moisture_pct, p.temp_c, p.lux, p.boot_count);

  ackReceived = false;
  esp_err_t r = esp_now_send(bridgeMac, (uint8_t*)&p, sizeof(p));
  if (r != ESP_OK) { Serial.printf("[ESPNOW] send err %d\n", r); return false; }
  uint32_t t0 = millis();
  while (!ackReceived && millis() - t0 < 500) delay(10);
  return ackReceived;
}

// =================== COMMAND HANDLER ===================
void handleCommand(const char* json) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, json) != DeserializationError::Ok) return;
  const char* type = doc["type"] | "";
  Serial.printf("[CMD] %s\n", type);

  if      (strcmp(type, "FORCE_READ") == 0)        { if (initEspNow()) sendReading(); }
  else if (strcmp(type, "SET_READ_INTERVAL") == 0) { prefs.begin("ecoadapt",false); prefs.putUInt("read_interval",  doc["value"]|DEFAULT_READ_INTERVAL_S);  prefs.end(); readIntervalS  = doc["value"]|DEFAULT_READ_INTERVAL_S; }
  else if (strcmp(type, "SET_CHECK_INTERVAL") == 0){ prefs.begin("ecoadapt",false); prefs.putUInt("check_interval", doc["value"]|DEFAULT_CHECK_INTERVAL_S); prefs.end(); checkIntervalS = doc["value"]|DEFAULT_CHECK_INTERVAL_S; }
  else if (strcmp(type, "SET_MODE") == 0)          { saveMode(doc["value"]|"NORMAL"); currentMode = doc["value"]|"NORMAL"; }
  else if (strcmp(type, "SLEEP") == 0)             { prefs.begin("ecoadapt",false); prefs.putBool("sleep_indef",true);  prefs.end(); sleepIndefinite=true; }
  else if (strcmp(type, "WAKE") == 0)              { prefs.begin("ecoadapt",false); prefs.putBool("sleep_indef",false); prefs.end(); sleepIndefinite=false; }
  else if (strcmp(type, "REBOOT") == 0)            { delay(200); ESP.restart(); }
  else if (strcmp(type, "RESET_CONFIG") == 0)      { resetConfig(); delay(200); ESP.restart(); }
}

// =================== SLEEP ===================
void deepSleepFor(uint32_t seconds) {
  Serial.printf("[SLEEP] %us\n", seconds);
  Serial.flush();
  esp_sleep_enable_timer_wakeup((uint64_t)seconds * 1000000ULL);
  esp_deep_sleep_start();
}

void runWakeCycle() {
  uint32_t cyclesPerRead = max((uint32_t)1, readIntervalS / max((uint32_t)1, checkIntervalS));
  bool shouldRead = firstBoot || (bootCount % cyclesPerRead == 0);

  if (!initEspNow()) { deepSleepFor(checkIntervalS); return; }

  if (shouldRead) {
    initSensors();
    sendReading();
  }

  // Listen for commands briefly
  uint32_t t0 = millis();
  while (millis() - t0 < 1500) {
    if (commandReceived) {
      handleCommand(pendingCommand);
      commandReceived = false;
      t0 = millis(); // extend window for chained commands
    }
    delay(10);
  }

  esp_now_deinit();
  WiFi.mode(WIFI_OFF);
  deepSleepFor(sleepIndefinite ? 3600 : checkIntervalS);
}

// =================== ARDUINO ===================
void setup() {
  Serial.begin(115200);
  delay(100);
  bootCount++;
  Serial.printf("\n=== EcoAdapt Pod boot #%d ===\n", bootCount);
  loadConfig();
  blink(2);
  runWakeCycle();
  firstBoot = false;
}

void loop() {}
