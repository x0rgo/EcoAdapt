/*
 * EcoAdapt Pod Firmware
 * Target: Seeed XIAO ESP32-C3
 *
 * Role: Sensor pod inside plant pot. Battery-powered (1200mAh LiPo).
 * Reads soil moisture, temperature, light. Sends to bridge via ESP-NOW.
 * Sleeps between readings to maximize battery life.
 *
 * Wakes briefly on a separate timer to check for incoming commands.
 *
 * Hardware:
 *   - HW-390 capacitive moisture sensor via ADS1015 (I2C addr 0x48)
 *   - VEML7700 lux sensor (I2C addr 0x10)
 *   - DS18B20 temperature probe on GPIO 4 (1-Wire, 4.7k pullup)
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
#include <Adafruit_ADS1X15.h>
#include <Adafruit_VEML7700.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <esp_sleep.h>

// ---------- Pin map (XIAO ESP32-C3) ----------
#define PIN_ONEWIRE        4    // DS18B20 data line (with 4.7k pullup to 3V3)
#define PIN_BATT_ADC       2    // optional battery voltage divider (skip if not wired)
#define PIN_LED_STATUS     LED_BUILTIN

// I2C: SDA=GPIO6, SCL=GPIO7 (XIAO C3 default Wire pins)

// ---------- Defaults ----------
static const uint32_t DEFAULT_READ_INTERVAL_S  = 300;  // 5 minutes
static const uint32_t DEFAULT_CHECK_INTERVAL_S = 30;
static const char*    DEFAULT_MODE             = "NORMAL";

// ---------- Wake reasons (stored in RTC memory) ----------
RTC_DATA_ATTR int  bootCount       = 0;
RTC_DATA_ATTR uint32_t lastReadEpoch = 0;
RTC_DATA_ATTR bool firstBoot       = true;

// ---------- Globals ----------
Preferences prefs;
Adafruit_ADS1015 ads;
Adafruit_VEML7700 veml;
OneWire oneWire(PIN_ONEWIRE);
DallasTemperature ds18b20(&oneWire);

bool adsOk  = false;
bool vemlOk = false;
bool dsOk   = false;

uint8_t bridgeMac[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF}; // broadcast until paired
String  podId        = "pod-default";
String  currentMode  = DEFAULT_MODE;

uint32_t readIntervalS  = DEFAULT_READ_INTERVAL_S;
uint32_t checkIntervalS = DEFAULT_CHECK_INTERVAL_S;
bool     sleepIndefinite = false;

volatile bool ackReceived       = false;
volatile bool commandReceived   = false;
char           pendingCommand[256] = {0};

// =================== UTIL ===================
void blink(int times, int ms = 80) {
  pinMode(PIN_LED_STATUS, OUTPUT);
  for (int i = 0; i < times; i++) {
    digitalWrite(PIN_LED_STATUS, LOW);  // XIAO LED is active-low
    delay(ms);
    digitalWrite(PIN_LED_STATUS, HIGH);
    delay(ms);
  }
}

float readBatteryVoltage() {
  // If you wire a divider on PIN_BATT_ADC, calibrate this. Otherwise return -1.
  // XIAO C3 has internal divider on the battery pad on some boards.
  // Safe default for now:
  return -1.0f;
}

// =================== NVS ===================
void loadConfig() {
  prefs.begin("ecoadapt", true); // read-only
  readIntervalS   = prefs.getUInt("read_interval",  DEFAULT_READ_INTERVAL_S);
  checkIntervalS  = prefs.getUInt("check_interval", DEFAULT_CHECK_INTERVAL_S);
  currentMode     = prefs.getString("mode",         DEFAULT_MODE);
  sleepIndefinite = prefs.getBool("sleep_indef",    false);
  podId           = prefs.getString("pod_id",       "pod-default");

  size_t macLen = prefs.getBytesLength("bridge_mac");
  if (macLen == 6) {
    prefs.getBytes("bridge_mac", bridgeMac, 6);
  }
  prefs.end();

  Serial.printf("[CFG] mode=%s read=%us check=%us sleep_indef=%d pod_id=%s\n",
                currentMode.c_str(), readIntervalS, checkIntervalS,
                sleepIndefinite ? 1 : 0, podId.c_str());
  Serial.printf("[CFG] bridge_mac=%02X:%02X:%02X:%02X:%02X:%02X\n",
                bridgeMac[0], bridgeMac[1], bridgeMac[2],
                bridgeMac[3], bridgeMac[4], bridgeMac[5]);
}

void saveMode(const String& m) {
  prefs.begin("ecoadapt", false);
  prefs.putString("mode", m);
  if (m == "DEMO")        { prefs.putUInt("read_interval", 60);   prefs.putUInt("check_interval", 10); }
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
  Wire.begin(); // SDA=6, SCL=7 on XIAO C3

  // ADS1015 for HW-390
  if (ads.begin(0x48)) {
    adsOk = true;
    ads.setGain(GAIN_ONE); // ±4.096V range, 2mV/step
    Serial.println("[SENS] ADS1015 OK");
  } else {
    Serial.println("[SENS] ADS1015 FAIL");
  }

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

// HW-390 calibration: dry ~2.6V (raw ~1300), wet ~1.2V (raw ~600).
// We map to 0-100% moisture.
int readMoisturePercent() {
  if (!adsOk) return -1;
  int16_t raw = ads.readADC_SingleEnded(0); // A0 of ADS1015
  // Constrain and map. Adjust DRY_RAW / WET_RAW per probe after calibration.
  const int16_t DRY_RAW = 1300;
  const int16_t WET_RAW = 600;
  int pct = map(raw, DRY_RAW, WET_RAW, 0, 100);
  pct = constrain(pct, 0, 100);
  return pct;
}

float readLux() {
  if (!vemlOk) return -1.0f;
  return veml.readLux();
}

float readTempC() {
  if (!dsOk) return -1000.0f;
  ds18b20.requestTemperatures();
  float t = ds18b20.getTempCByIndex(0);
  if (t == DEVICE_DISCONNECTED_C) return -1000.0f;
  return t;
}

// =================== ESP-NOW ===================
typedef struct __attribute__((packed)) {
  char     type[8];      // "READING" or "ACK" or "PAIR"
  char     pod_id[24];
  uint32_t timestamp;    // millis-since-boot or epoch if synced
  int      moisture_pct; // 0-100, -1 if invalid
  float    temp_c;       // -1000 if invalid
  float    lux;          // -1 if invalid
  float    battery_v;    // -1 if not wired
  uint8_t  boot_count;
} ReadingPacket;

typedef struct __attribute__((packed)) {
  char type[8];          // "CMD"
  char payload[200];     // JSON command from server, forwarded by bridge
} CommandPacket;

void onDataSent(const uint8_t* mac, esp_now_send_status_t status) {
  ackReceived = (status == ESP_NOW_SEND_SUCCESS);
  Serial.printf("[ESPNOW] send status=%d to %02X:%02X:%02X:%02X:%02X:%02X\n",
    status, mac[0],mac[1],mac[2],mac[3],mac[4],mac[5]);
}

void onDataRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  if (len < 4) return;
  // Try to parse as a CommandPacket
  if (len >= (int)sizeof(CommandPacket) - 8 && memcmp(data, "CMD", 3) == 0) {
    CommandPacket cmd;
    memset(&cmd, 0, sizeof(cmd));
    memcpy(&cmd, data, min((int)sizeof(cmd), len));
    strncpy(pendingCommand, cmd.payload, sizeof(pendingCommand) - 1);
    commandReceived = true;
    Serial.printf("[ESPNOW] CMD received: %s\n", pendingCommand);

    // First time we hear from the bridge, save its MAC for unicast next time
    if (bridgeMac[0] == 0xFF) {
      saveBridgeMac(info->src_addr);
    }
  } else if (len >= 3 && memcmp(data, "PAIR", 4) == 0) {
    // PAIR beacon from bridge: save its MAC
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
  ReadingPacket p = {};
  strncpy(p.type, "READING", sizeof(p.type)-1);
  strncpy(p.pod_id, podId.c_str(), sizeof(p.pod_id)-1);
  p.timestamp    = millis();
  p.moisture_pct = readMoisturePercent();
  p.temp_c       = readTempC();
  p.lux          = readLux();
  p.battery_v    = readBatteryVoltage();
  p.boot_count   = (uint8_t)(bootCount & 0xFF);

  Serial.printf("[READ] m=%d%% t=%.1fC lux=%.1f batt=%.2fV boot=%d\n",
    p.moisture_pct, p.temp_c, p.lux, p.battery_v, p.boot_count);

  ackReceived = false;
  esp_err_t r = esp_now_send(bridgeMac, (uint8_t*)&p, sizeof(p));
  if (r != ESP_OK) {
    Serial.printf("[ESPNOW] send err %d\n", r);
    return false;
  }
  // Wait briefly for callback
  uint32_t t0 = millis();
  while (!ackReceived && millis() - t0 < 500) { delay(10); }
  return ackReceived;
}

// =================== COMMAND HANDLER ===================
void handleCommand(const char* json) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) {
    Serial.printf("[CMD] JSON parse err: %s\n", err.c_str());
    return;
  }
  const char* type = doc["type"] | "";
  Serial.printf("[CMD] type=%s\n", type);

  if (strcmp(type, "FORCE_READ") == 0) {
    if (!initEspNow()) return;
    sendReading();
  }
  else if (strcmp(type, "SET_READ_INTERVAL") == 0) {
    uint32_t v = doc["value"] | DEFAULT_READ_INTERVAL_S;
    prefs.begin("ecoadapt", false);
    prefs.putUInt("read_interval", v);
    prefs.end();
    readIntervalS = v;
  }
  else if (strcmp(type, "SET_CHECK_INTERVAL") == 0) {
    uint32_t v = doc["value"] | DEFAULT_CHECK_INTERVAL_S;
    prefs.begin("ecoadapt", false);
    prefs.putUInt("check_interval", v);
    prefs.end();
    checkIntervalS = v;
  }
  else if (strcmp(type, "SET_MODE") == 0) {
    const char* m = doc["value"] | "NORMAL";
    saveMode(m);
    currentMode = m;
  }
  else if (strcmp(type, "SLEEP") == 0) {
    prefs.begin("ecoadapt", false);
    prefs.putBool("sleep_indef", true);
    prefs.end();
    sleepIndefinite = true;
  }
  else if (strcmp(type, "WAKE") == 0) {
    prefs.begin("ecoadapt", false);
    prefs.putBool("sleep_indef", false);
    prefs.end();
    sleepIndefinite = false;
  }
  else if (strcmp(type, "REBOOT") == 0) {
    delay(200);
    ESP.restart();
  }
  else if (strcmp(type, "RESET_CONFIG") == 0) {
    resetConfig();
    delay(200);
    ESP.restart();
  }
}

// =================== SLEEP ===================
void deepSleepFor(uint32_t seconds) {
  Serial.printf("[SLEEP] %u s\n", seconds);
  Serial.flush();
  esp_sleep_enable_timer_wakeup((uint64_t)seconds * 1000000ULL);
  esp_deep_sleep_start();
}

// Decide what to do this wake cycle:
//   - if it has been >= readIntervalS since last reading => take + send a reading
//   - else => brief command-listen window, then sleep again
void runWakeCycle() {
  uint32_t nowSec = (uint32_t)(esp_timer_get_time() / 1000000ULL) + lastReadEpoch;
  // Approximate: we don't have RTC time; use a counter pattern.
  // Strategy: every wake increments check counter; we read sensors when
  // (bootCount % (readIntervalS / checkIntervalS)) == 0.
  uint32_t cyclesPerRead = max((uint32_t)1, readIntervalS / max((uint32_t)1, checkIntervalS));
  bool shouldRead = firstBoot || (bootCount % cyclesPerRead == 0);

  if (!initEspNow()) {
    Serial.println("[ESPNOW] init failed, sleeping");
    deepSleepFor(checkIntervalS);
  }

  if (shouldRead) {
    initSensors();
    sendReading();
  }

  // Brief command-listen window
  uint32_t listenMs = 1500;
  uint32_t t0 = millis();
  while (millis() - t0 < listenMs) {
    if (commandReceived) {
      handleCommand(pendingCommand);
      commandReceived = false;
      // After a command, listen a bit longer for chained commands
      t0 = millis();
    }
    delay(10);
  }

  esp_now_deinit();
  WiFi.mode(WIFI_OFF);

  if (sleepIndefinite) {
    // Sleep for a long time but still wake occasionally to check for WAKE cmd
    deepSleepFor(3600); // 1h
  } else {
    deepSleepFor(checkIntervalS);
  }
}

// =================== ARDUINO ===================
void setup() {
  Serial.begin(115200);
  delay(100);
  bootCount++;
  Serial.printf("\n=== EcoAdapt Pod boot #%d ===\n", bootCount);

  loadConfig();

  // First boot: send a PAIR-style packet by broadcasting a reading
  // so the bridge learns our MAC.
  blink(2);

  runWakeCycle();
  firstBoot = false;
  // Should never reach here — runWakeCycle ends in deep sleep
}

void loop() {
  // Unused; setup() ends in deep sleep
}
