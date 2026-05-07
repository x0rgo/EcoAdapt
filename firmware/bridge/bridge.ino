/*
 * EcoAdapt Bridge Firmware
 * Target: Seeed XIAO ESP32-C3
 *
 * Role: USB-powered bridge. Receives sensor packets from pod via ESP-NOW,
 * forwards them to the cloud server over HTTPS, and polls the server for
 * commands which it relays back to the pod via ESP-NOW.
 *
 * If no WiFi is configured, runs a captive portal so the user can enter
 * SSID/password via a web UI.
 *
 * Auto-flash compatible: API key, server URL, and pod_id are all stored
 * in NVS and can be written by the web flasher AFTER this firmware is
 * installed. This means ONE universal .bin file works for every user.
 *
 * NVS keys (preferences namespace "ecoadapt"):
 *   wifi_ssid         string
 *   wifi_pass         string
 *   api_key           string  per-user API key from the dashboard
 *   server_url        string  e.g. https://ecoadapt.onrender.com
 *   pod_mac           bytes   6-byte MAC of the paired pod (optional)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <NimBLEDevice.h>

// ---------- Defaults ----------
#define AP_SSID            "EcoAdapt-Setup"
#define AP_PASS            ""           // open AP for setup
#define DEFAULT_SERVER_URL "https://ecoadapt.onrender.com"
#define POLL_INTERVAL_MS   5000
#define LED_BUILTIN        8    // XIAO ESP32-C3
#define BLE_PROV_TIMEOUT_MS 60000      // 60s BLE provisioning window before falling back to AP

// BLE provisioning UUIDs (random, but stable so the dashboard can scan for them)
#define BLE_SVC_UUID       "ec0adab1-2025-4b1d-9e91-100000000000"
#define BLE_CHR_WIFI_UUID  "ec0adab1-2025-4b1d-9e91-100000000001"  // write: JSON {ssid,pass,api_key?,server_url?}
#define BLE_CHR_STATUS_UUID "ec0adab1-2025-4b1d-9e91-100000000002" // notify: status string

// ---------- Globals ----------
Preferences prefs;
WebServer   web(80);
DNSServer   dns;

String wifiSsid;
String wifiPass;
String apiKey;
String serverUrl = DEFAULT_SERVER_URL;
uint8_t podMac[6] = {0};
bool podPaired = false;

bool   apMode = false;
unsigned long lastPoll = 0;

// ---------- Packet structs (must match pod) ----------
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

// Latest reading buffered for offline dashboard
ReadingPacket lastReading = {};
bool hasReading = false;
unsigned long lastReadingMs = 0;

// =================== NVS ===================
void loadConfig() {
  prefs.begin("ecoadapt", true);
  wifiSsid  = prefs.getString("wifi_ssid",  "");
  wifiPass  = prefs.getString("wifi_pass",  "");
  apiKey    = prefs.getString("api_key",    "");
  serverUrl = prefs.getString("server_url", DEFAULT_SERVER_URL);
  size_t macLen = prefs.getBytesLength("pod_mac");
  if (macLen == 6) {
    prefs.getBytes("pod_mac", podMac, 6);
    podPaired = true;
  }
  prefs.end();

  Serial.printf("[CFG] ssid=%s api_key=%s url=%s podPaired=%d\n",
    wifiSsid.c_str(),
    apiKey.length() ? "(set)" : "(empty)",
    serverUrl.c_str(),
    podPaired ? 1 : 0);
}

void saveWifi(const String& ssid, const String& pass) {
  prefs.begin("ecoadapt", false);
  prefs.putString("wifi_ssid", ssid);
  prefs.putString("wifi_pass", pass);
  prefs.end();
  wifiSsid = ssid;
  wifiPass = pass;
}

void savePodMac(const uint8_t* mac) {
  prefs.begin("ecoadapt", false);
  prefs.putBytes("pod_mac", mac, 6);
  prefs.end();
  memcpy(podMac, mac, 6);
  podPaired = true;
}

// =================== ESP-NOW ===================
void onDataRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  if (len < 4) return;

  if (memcmp(data, "READING", 7) == 0 && len >= (int)sizeof(ReadingPacket)) {
    ReadingPacket p;
    memcpy(&p, data, sizeof(p));
    lastReading = p;
    hasReading = true;
    lastReadingMs = millis();

    Serial.printf("[POD] reading from %s m=%d t=%.1f lux=%.1f\n",
      p.pod_id, p.moisture_pct, p.temp_c, p.lux);

    // Save pod MAC if not paired
    if (!podPaired) {
      savePodMac(info->src_addr);
      Serial.println("[POD] paired");
    }
  }
}

void onDataSent(const wifi_tx_info_t* info, esp_now_send_status_t status) {
  Serial.printf("[ESPNOW] cmd send status=%d\n", status);
}

bool initEspNow() {
  // ESP-NOW shares the WiFi MAC; both pod & bridge must be on the same channel.
  // When connected to a router, the channel is fixed by the AP. When in AP
  // mode for the captive portal, we use the AP's channel.
  if (esp_now_init() != ESP_OK) {
    Serial.println("[ESPNOW] init FAIL");
    return false;
  }
  esp_now_register_recv_cb(onDataRecv);
  esp_now_register_send_cb(onDataSent);

  // Add broadcast peer so we can answer pods that haven't paired yet
  esp_now_peer_info_t peer = {};
  uint8_t bcast[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
  memcpy(peer.peer_addr, bcast, 6);
  peer.channel = 0;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  // If paired, also add the unicast peer
  if (podPaired) {
    esp_now_peer_info_t up = {};
    memcpy(up.peer_addr, podMac, 6);
    up.channel = 0;
    up.encrypt = false;
    esp_now_add_peer(&up);
  }
  return true;
}

void forwardCommandToPod(const String& jsonPayload) {
  CommandPacket cmd = {};
  strncpy(cmd.type, "CMD", sizeof(cmd.type)-1);
  strncpy(cmd.payload, jsonPayload.c_str(), sizeof(cmd.payload)-1);

  uint8_t target[6];
  if (podPaired) {
    memcpy(target, podMac, 6);
  } else {
    memset(target, 0xFF, 6); // broadcast
  }
  esp_err_t r = esp_now_send(target, (uint8_t*)&cmd, sizeof(cmd));
  Serial.printf("[ESPNOW] forward cmd r=%d payload=%s\n", r, jsonPayload.c_str());
}

// =================== WIFI / HTTP ===================
bool connectWifi(uint32_t timeoutMs = 20000) {
  if (wifiSsid.isEmpty()) return false;
  WiFi.mode(WIFI_STA);
  WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
  Serial.printf("[WIFI] connecting to %s\n", wifiSsid.c_str());
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < timeoutMs) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WIFI] OK ip=%s\n", WiFi.localIP().toString().c_str());
    return true;
  }
  Serial.println("[WIFI] FAIL");
  return false;
}

bool postReading(const ReadingPacket& p) {
  if (apiKey.isEmpty() || WiFi.status() != WL_CONNECTED) return false;

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(30);        // seconds — allows for Render cold-start
  HTTPClient http;
  http.setTimeout(30000);       // ms

  String url = serverUrl + "/api/reading";
  Serial.printf("[HTTP] url=%s key=%s\n", url.c_str(), apiKey.substring(0,8).c_str());
  if (!http.begin(client, url)) {
    Serial.println("[HTTP] begin FAIL");
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", apiKey);

  StaticJsonDocument<256> doc;
  doc["moisture"]    = p.moisture_pct;
  doc["temperature"] = p.temp_c;
  doc["light"]       = p.lux;
  doc["battery"]     = p.battery_v;
  String body;
  serializeJson(doc, body);

  int code = http.POST(body);
  Serial.printf("[HTTP] POST /api/reading => %d\n", code);
  http.end();
  return code >= 200 && code < 300;
}

void pollCommands() {
  if (apiKey.isEmpty() || WiFi.status() != WL_CONNECTED) return;

  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;

  String url = serverUrl + "/api/commands/pending";
  if (!http.begin(client, url)) return;
  http.addHeader("X-API-Key", apiKey);

  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    StaticJsonDocument<1024> doc;
    if (deserializeJson(doc, body) == DeserializationError::Ok) {
      JsonArray cmds = doc.as<JsonArray>();
      for (JsonObject cmd : cmds) {
        String s;
        serializeJson(cmd, s);
        forwardCommandToPod(s);
      }
    }
  }
  http.end();
}

// =================== BLE PROVISIONING ===================
// Phase 2 of the provisioning fallback chain:
//   1. NVS already has WiFi creds (from web flasher) -> use them
//   2. Else, advertise over BLE for 60s. Phone scans, sends WiFi creds.
//   3. Else, fall back to captive portal AP.
//
// Protocol: phone writes JSON to BLE_CHR_WIFI_UUID:
//   { "ssid": "MyWifi", "pass": "secret", "api_key": "ek_..." (optional),
//     "server_url": "..." (optional) }
// Bridge replies via the status characteristic, then reboots to connect.

static volatile bool bleProvDone = false;

class WifiWriteCb : public NimBLECharacteristicCallbacks {
  NimBLECharacteristic* _stat;
public:
  WifiWriteCb(NimBLECharacteristic* stat) : _stat(stat) {}
  void onWrite(NimBLECharacteristic* chr, NimBLEConnInfo& connInfo) override {
    std::string val = chr->getValue();
    Serial.printf("[BLE] wifi write: %s\n", val.c_str());
    StaticJsonDocument<512> doc;
    if (deserializeJson(doc, val) != DeserializationError::Ok) {
      _stat->setValue("err:json");
      _stat->notify();
      return;
    }
    const char* s = doc["ssid"] | "";
    const char* p = doc["pass"] | "";
    const char* k = doc["api_key"] | "";
    const char* u = doc["server_url"] | "";
    if (!s || !*s) {
      _stat->setValue("err:no-ssid");
      _stat->notify();
      return;
    }
    prefs.begin("ecoadapt", false);
    prefs.putString("wifi_ssid", s);
    prefs.putString("wifi_pass", p);
    if (k && *k) prefs.putString("api_key", k);
    if (u && *u) prefs.putString("server_url", u);
    prefs.end();

    _stat->setValue("ok:reboot");
    _stat->notify();
    bleProvDone = true;
  }
};

bool runBleProvisioning(uint32_t timeoutMs) {
  Serial.println("[BLE] starting provisioning advertisement");
  String devName = "EcoAdapt-" + String((uint32_t)(ESP.getEfuseMac() & 0xFFFF), HEX);
  NimBLEDevice::init(devName.c_str());
  NimBLEDevice::setPower(ESP_PWR_LVL_P9);

  NimBLEServer* server = NimBLEDevice::createServer();
  NimBLEService* svc = server->createService(BLE_SVC_UUID);

  NimBLECharacteristic* wifiChr = svc->createCharacteristic(
    BLE_CHR_WIFI_UUID,
    NIMBLE_PROPERTY::WRITE
  );

  NimBLECharacteristic* statusChr = svc->createCharacteristic(
    BLE_CHR_STATUS_UUID,
    NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
  );
  statusChr->setValue("waiting");

  wifiChr->setCallbacks(new WifiWriteCb(statusChr));

  svc->start();
  NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
  adv->addServiceUUID(BLE_SVC_UUID);
  adv->setName(devName.c_str());
  adv->start();

  Serial.printf("[BLE] advertising as %s for %u ms\n", devName.c_str(), timeoutMs);

  uint32_t t0 = millis();
  while (millis() - t0 < timeoutMs && !bleProvDone) {
    delay(100);
  }

  if (bleProvDone) {
    Serial.println("[BLE] credentials received via BLE");
    delay(500); // let notification flush
  } else {
    Serial.println("[BLE] timed out");
  }

  adv->stop();
  NimBLEDevice::deinit(true);
  return bleProvDone;
}

// =================== CAPTIVE PORTAL ===================
const char PORTAL_HTML[] PROGMEM = R"HTML(
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EcoAdapt Setup</title>
<style>
  :root{--g:#2d6a4f;--bg:#f1faee;--card:#fff;--ink:#1d3557}
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,system-ui,sans-serif;background:var(--bg);color:var(--ink);min-height:100vh;display:grid;place-items:center;padding:24px}
  .card{background:var(--card);border-radius:20px;box-shadow:0 8px 32px rgba(0,0,0,.08);padding:32px;max-width:420px;width:100%}
  h1{margin:0 0 4px;font-size:24px}
  .sub{color:#666;font-size:14px;margin-bottom:24px}
  label{display:block;font-size:13px;font-weight:600;margin:14px 0 6px}
  input,select{width:100%;padding:12px 14px;border:1px solid #ddd;border-radius:10px;font-size:15px;background:#fafafa}
  input:focus,select:focus{outline:none;border-color:var(--g);background:#fff}
  button{margin-top:20px;width:100%;padding:14px;background:var(--g);color:#fff;border:0;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer}
  button:hover{background:#1b4332}
  .leaf{font-size:32px}
  .row{display:flex;gap:8px;align-items:center}
  .scan{flex:0 0 auto;padding:8px 12px;font-size:12px;background:#e9ecef;color:#1d3557;border-radius:8px;cursor:pointer;border:0}
  .ok{color:#2d6a4f;font-weight:600;margin-top:12px}
</style></head>
<body>
<div class="card">
  <div class="leaf">🌿</div>
  <h1>EcoAdapt Bridge Setup</h1>
  <div class="sub">Last-resort WiFi setup. If you've used the web flasher or BLE pairing, you shouldn't need this.</div>
  <form id="f" action="/save" method="POST">
    <label>WiFi network</label>
    <div class="row">
      <select name="ssid" id="ssid"><option>Scan to load networks</option></select>
      <button type="button" class="scan" onclick="scan()">Scan</button>
    </div>
    <label>WiFi password</label>
    <input name="pass" type="password" placeholder="Leave empty if open">
    <label>API key (from your EcoAdapt dashboard)</label>
    <input name="api_key" placeholder="ek_...." required>
    <label>Server URL</label>
    <input name="server_url" value="https://ecoadapt.onrender.com">
    <button type="submit">Save & Reboot</button>
  </form>
</div>
<script>
async function scan(){
  const r = await fetch('/scan'); const j = await r.json();
  const sel = document.getElementById('ssid'); sel.innerHTML='';
  j.networks.forEach(n=>{
    const o = document.createElement('option'); o.value=n.ssid;
    o.textContent = n.ssid + ' ('+n.rssi+' dBm)'; sel.appendChild(o);
  });
}
scan();
</script>
</body></html>
)HTML";

const char STATUS_HTML[] PROGMEM = R"HTML(
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EcoAdapt Bridge</title>
<style>
  body{font-family:system-ui;background:#f1faee;color:#1d3557;padding:24px;max-width:560px;margin:auto}
  .card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 4px 16px rgba(0,0,0,.06);margin-bottom:16px}
  h1{margin:0 0 4px} .k{color:#666;font-size:13px} .v{font-size:18px;font-weight:600}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .ok{color:#2d6a4f}.bad{color:#e63946}
</style></head>
<body>
<div class="card">
  <h1>🌿 EcoAdapt Bridge</h1>
  <div class="k">Offline dashboard</div>
</div>
<div class="card">
  <div class="grid">
    <div><div class="k">Moisture</div><div class="v" id="m">—</div></div>
    <div><div class="k">Temperature</div><div class="v" id="t">—</div></div>
    <div><div class="k">Light</div><div class="v" id="l">—</div></div>
    <div><div class="k">Battery</div><div class="v" id="b">—</div></div>
  </div>
</div>
<div class="card">
  <div class="k">WiFi</div><div class="v" id="w">—</div>
  <div class="k" style="margin-top:8px">Pod paired</div><div class="v" id="p">—</div>
  <div class="k" style="margin-top:8px">Last reading</div><div class="v" id="r">—</div>
  <p><a href="/setup">Reconfigure WiFi & API key</a></p>
</div>
<script>
async function tick(){
  const r = await fetch('/status'); const j = await r.json();
  document.getElementById('m').textContent = j.moisture==-1?'—':j.moisture+'%';
  document.getElementById('t').textContent = j.temp<-100?'—':j.temp.toFixed(1)+' °C';
  document.getElementById('l').textContent = j.lux<0?'—':j.lux.toFixed(0)+' lx';
  document.getElementById('b').textContent = j.batt<0?'USB':j.batt.toFixed(2)+' V';
  document.getElementById('w').textContent = j.wifi || 'disconnected';
  document.getElementById('p').textContent = j.paired ? 'yes' : 'no';
  document.getElementById('r').textContent = j.age_s+' s ago';
}
setInterval(tick,3000); tick();
</script>
</body></html>
)HTML";

void handlePortal()    { web.send_P(200, "text/html", PORTAL_HTML); }
void handleSetupPage() { web.send_P(200, "text/html", PORTAL_HTML); }
void handleRoot() {
  if (apMode) handlePortal();
  else        web.send_P(200, "text/html", STATUS_HTML);
}

void handleScan() {
  int n = WiFi.scanNetworks();
  StaticJsonDocument<1024> doc;
  JsonArray arr = doc.createNestedArray("networks");
  for (int i = 0; i < n && i < 12; i++) {
    JsonObject o = arr.createNestedObject();
    o["ssid"] = WiFi.SSID(i);
    o["rssi"] = WiFi.RSSI(i);
  }
  String out; serializeJson(doc, out);
  web.send(200, "application/json", out);
}

void handleSave() {
  String ssid = web.arg("ssid");
  String pass = web.arg("pass");
  String key  = web.arg("api_key");
  String url  = web.arg("server_url");

  prefs.begin("ecoadapt", false);
  if (ssid.length()) prefs.putString("wifi_ssid", ssid);
  prefs.putString("wifi_pass", pass);
  if (key.length())  prefs.putString("api_key", key);
  if (url.length())  prefs.putString("server_url", url);
  prefs.end();

  web.send(200, "text/html",
    "<html><body style='font-family:system-ui;padding:24px'>"
    "<h2>Saved! Rebooting…</h2></body></html>");
  delay(800);
  ESP.restart();
}

void handleStatus() {
  StaticJsonDocument<256> doc;
  doc["moisture"] = hasReading ? lastReading.moisture_pct : -1;
  doc["temp"]     = hasReading ? lastReading.temp_c       : -1000.0f;
  doc["lux"]      = hasReading ? lastReading.lux          : -1.0f;
  doc["batt"]     = hasReading ? lastReading.battery_v    : -1.0f;
  doc["wifi"]     = (WiFi.status() == WL_CONNECTED) ? WiFi.SSID() : "";
  doc["paired"]   = podPaired;
  doc["age_s"]    = hasReading ? (millis() - lastReadingMs) / 1000UL : 0UL;
  String out; serializeJson(doc, out);
  web.send(200, "application/json", out);
}

void startAP() {
  apMode = true;
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID);
  IPAddress ip = WiFi.softAPIP();
  Serial.printf("[AP] %s ip=%s\n", AP_SSID, ip.toString().c_str());
  dns.start(53, "*", ip);
  web.on("/",       handleRoot);
  web.on("/setup",  handleSetupPage);
  web.on("/scan",   handleScan);
  web.on("/save",   HTTP_POST, handleSave);
  // Captive-portal probes (Apple, Android, Windows)
  web.onNotFound(handlePortal);
  web.begin();
}

void startStatusServer() {
  web.on("/",       handleRoot);
  web.on("/setup",  handleSetupPage);
  web.on("/scan",   handleScan);
  web.on("/save",   HTTP_POST, handleSave);
  web.on("/status", handleStatus);
  web.begin();
  Serial.printf("[HTTP] status server on http://%s/\n",
                WiFi.localIP().toString().c_str());
}

// =================== ARDUINO ===================
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== EcoAdapt Bridge ===");

  loadConfig();

  // ---------- Provisioning fallback chain ----------
  // Tier 1: NVS already has WiFi creds (from web flasher or previous setup)
  // Tier 2: BLE provisioning window (60s)
  // Tier 3: Captive portal AP

  bool wifiOk = false;
  if (!wifiSsid.isEmpty()) {
    Serial.println("[BOOT] tier 1: NVS-staged WiFi");
    wifiOk = connectWifi();
  }

  if (!wifiOk) {
    Serial.println("[BOOT] tier 2: BLE provisioning");
    bool gotBle = runBleProvisioning(BLE_PROV_TIMEOUT_MS);
    if (gotBle) {
      // Reload NVS — BLE callback wrote new values
      loadConfig();
      wifiOk = connectWifi();
    }
  }

  if (wifiOk) {
    initEspNow();
    startStatusServer();
  } else {
    Serial.println("[BOOT] tier 3: captive portal");
    startAP();
    initEspNow();
  }
}

void loop() {
  dns.processNextRequest();
  web.handleClient();

  static unsigned long lastForward = 0;
  unsigned long now = millis();

  // Forward latest reading (if any) on a debounced cadence
  if (hasReading && now - lastForward > 1000) {
    lastForward = now;
    if (!apMode) postReading(lastReading);
    hasReading = false; // mark consumed; next packet sets it again
  }

  // Poll for commands
  if (!apMode && now - lastPoll > POLL_INTERVAL_MS) {
    lastPoll = now;
    pollCommands();
  }

  delay(5);
}
