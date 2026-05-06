# EcoAdapt

> A living plant companion system. Your plant monitors itself, develops a personality, and speaks to you.

![Python](https://img.shields.io/badge/Python-3.12-green?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey?style=flat-square&logo=flask)
![Arduino](https://img.shields.io/badge/Arduino-ESP32--C3-teal?style=flat-square&logo=arduino)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

---

## What is EcoAdapt?

EcoAdapt turns a houseplant into an AI-powered Tamagotchi companion. Real soil sensors feed live data to a cloud server, which generates in-character speech based on your plant's mood, needs, and life stage. The plant grows over time, remembers neglect, reacts to its environment, and talks back.

Built as a science fair project exploring whether AI-driven plant personification improves care adherence compared to traditional alert-based systems.

---

## How it works

```
Sensor Pod (XIAO ESP32-C3)
  └── Capacitive moisture · DS18B20 soil temp · VEML7700 lux
  └── Deep sleep between readings  (~6 months battery life)
  └── Transmits via ESP-NOW ──────────────────────────────►

Bridge (XIAO ESP32-C3)
  └── Always-on, USB-powered
  └── Receives ESP-NOW from pod
  └── Forwards to server via WiFi (HTTP + API key auth)
  └── Falls back to local captive-portal AP if no internet
  └── BLE pairing + NVS-staged WiFi provisioning ─────────►

Cloud Server (Flask on Render)
  └── SQLite · per-user readings, plant config, commands
  └── AI dialogue via OpenRouter (Mistral / Claude / Gemini)
  └── Browser TTS with streaming audio
  └── WebSocket live push to dashboard
  └── Web Serial firmware flasher (/flash)
  └── Web Bluetooth pairing page (/pair) ──────────────────►

Web Dashboard
  └── Live sensor gauges · history charts
  └── Tamagotchi pet (needs, happiness, XP, 5 life stages)
  └── Chat with your plant
  └── Species selector · AI model picker
  └── Pod command queue (read interval, mode, reboot)
  └── One-click firmware flash + API key delivery
```

---

## Features

- **AI plant personality** — species-specific characters (dramatic peace lily, stoic cactus, anxious fern). Swappable AI model from the dashboard (Mistral, Claude, Gemini, Llama).
- **Tamagotchi mechanics** — needs system, happiness score, XP, five life stages from seed to bloom
- **Achievements** — unlockable milestones for care, chat, growth, neglect, and general chaos
- **Browser TTS** — streaming speech with configurable voice, speed, and format
- **Web firmware flasher** — one-click in-browser flashing via Web Serial (Chrome/Edge). NVS partition built server-side so the same .bin works for every user.
- **BLE pairing** — Web Bluetooth page lets you push WiFi credentials wirelessly post-flash
- **3-tier WiFi provisioning** — NVS-staged → BLE → captive-portal fallback
- **Research-backed care thresholds** — moisture, temp, and light ranges per species from horticultural references
- **Night mode** — suppresses light/energy alerts between 21:00 and 07:00
- **Neglect memory** — the plant remembers when it was ignored and brings it up unprompted
- **Public plant pages** — shareable read-only view at `/api/public/<username>`
- **Multi-user** — full account isolation, per-user API keys, per-user sensor history

---

## Hardware

| Component | Purpose |
|---|---|
| Seeed XIAO ESP32-C3 × 2 | Sensor pod + WiFi bridge |
| HW-390 capacitive moisture sensor | Soil moisture (analog) |
| DS18B20 waterproof probe | Soil temperature (OneWire) |
| Adafruit VEML7700 | Ambient light in lux (I²C) |
| 1200 mAh LiPo + charger module | Pod battery (~6 months per charge) |

---

## Software Stack

| Layer | Tech |
|---|---|
| Pod + Bridge firmware | Arduino C++ (ESP32 core 3.x, ESP-IDF NVS, ESP-NOW) |
| Backend | Python 3.12, Flask, Flask-SocketIO, APScheduler |
| Database | SQLite (persistent disk on Render) |
| AI | OpenRouter API — Mistral Nemo default, Claude/Gemini/Llama selectable |
| TTS | OpenAI TTS / Google Gemini TTS via OpenRouter |
| Frontend | Vanilla HTML/JS, Chart.js, Socket.IO client |
| Firmware flasher | esptool-js (Web Serial), Web Bluetooth API |
| Hosting | Render.com (free tier) |

---

## Project Structure

```
EcoAdapt/
├── main.py                     # Flask app factory + APScheduler
├── requirements.txt
├── render.yaml                 # Render deployment config
│
├── lib/                        # Application package
│   ├── api.py                  # REST API routes (/api/*)
│   ├── auth.py                 # Login, sessions, API key management
│   ├── db.py                   # SQLite schema + all data access functions
│   ├── ws.py                   # Socket.IO events
│   ├── flash_routes.py         # Firmware flasher blueprint (/flash, /firmware/*)
│   ├── personality.py          # AI dialogue + daily check-ins
│   ├── tts.py                  # TTS generation + streaming
│   ├── thresholds.py           # Care checks, mood, recommendations
│   ├── tamagotchi.py           # Needs, happiness, XP, life stages
│   ├── achievements.py         # Achievement unlock + counter logic
│   └── species.py              # Species care profiles
│
├── static/
│   ├── index.html              # Main dashboard (single-page app)
│   ├── flash.html              # Web Serial firmware flasher
│   └── pair.html               # Web Bluetooth pairing page
│
├── firmware/
│   ├── bridge/bridge.ino       # Bridge firmware (ESP-NOW + WiFi + BLE + captive portal)
│   ├── pod/pod.ino             # Pod firmware (sensors + deep sleep + ESP-NOW)
│   └── build_scripts/
│       ├── setup.sh            # One-time: install arduino-cli board + libraries
│       └── build.sh            # Compile both sketches → instance/firmware/*.bin
│
└── instance/firmware/          # Built .bin files served by Flask (gitignored pattern, tracked manually)
    ├── bridge.bin
    ├── pod.bin
    ├── bootloader.bin
    └── partitions.bin
```

---

## Getting Started

### Requirements

- Python 3.12+
- An [OpenRouter](https://openrouter.ai) API key (free tier works)
- Arduino CLI + ESP32 board package if building firmware

### Local setup

```bash
git clone https://github.com/x0rgo/EcoAdapt.git
cd EcoAdapt
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Create `.env`:
```env
OPENROUTER_API_KEY=sk-or-...
SECRET_KEY=pick-something-random
DEBUG=true
DB_PATH=ecoadapt.db
```

Run:
```bash
python main.py
```

Open `http://localhost:5000`, register an account, and you're in.

---

## Firmware

The bridge and pod are compiled once; per-user config (API key, server URL, optional WiFi) is written to a separate NVS partition at flash time — the same `.bin` works for every user.

### Build

Requires [arduino-cli](https://arduino.github.io/arduino-cli/latest/installation/).

```bash
cd firmware/build_scripts
bash setup.sh    # one-time: installs ESP32 board + libraries
bash build.sh    # outputs to instance/firmware/
```

On Windows, run in Git Bash (`winget install ArduinoSA.CLI` first).

### Flash

1. Go to `http://localhost:5000/flash` (or the Render URL) in **Chrome or Edge**
2. Log in — your API key auto-fills
3. Optionally enter WiFi credentials to pre-stage them
4. Plug in the XIAO ESP32-C3, hold BOOT + tap RESET
5. Click **⚡ Flash my bridge**

The flasher builds a 24 KB NVS image server-side and flashes all partitions in one pass via Web Serial.

Alternatively, download the `.bin + script` bundle and flash manually with esptool.

---

## Deploying to Render

1. Push this repo to GitHub
2. Connect to [Render](https://render.com), create a **Web Service**
3. Build command: `pip install -r requirements.txt`
4. Start command: `python main.py`
5. Add environment variables: `OPENROUTER_API_KEY`, `SECRET_KEY`
6. Add a **Persistent Disk** at `/data`, set `DB_PATH=/data/ecoadapt.db`

The `render.yaml` in this repo pre-configures all of the above.

---

## API Key Auth

The bridge authenticates every request with the `X-API-Key` header:

```
POST /api/reading        — sensor data upload
GET  /api/commands/pending — command poll
POST /api/commands/<id>/ack — acknowledge command
```

Get your key from the dashboard → Settings → **Your API Key**. Regenerate at any time (your bridge will need reflashing).

---

## Species Threshold Sources

| Parameter | Source |
|---|---|
| Soil moisture | [Elm Dirt Moisture Meter Guide](https://www.elmdirt.com/blogs/news/moisture-meter-guide) |
| Light levels (lux) | [Wikiversity Houseplant Care](https://en.wikiversity.org/wiki/Houseplant_care) · [House Plant Journal](https://www.houseplantjournal.com) |
| Temperature ranges | [Cielo Blog](https://cielowigle.com/blog/temperature-for-plants/) · [University of Arkansas Extension](https://www.uaex.uada.edu/yard-garden/home-landscape/docs/Temperature%20Requirements%20of%20Selected%20House%20Plants.pdf) |
| Cactus/succulent | [Cactus & Succulent Society of MA](https://www.cssma.org/succulent-care) |

---

## Roadmap

- [x] Pod firmware — sensors, deep sleep, ESP-NOW TX
- [x] Bridge firmware — ESP-NOW RX, WiFi, HTTP, BLE, captive portal
- [x] Web firmware flasher (Web Serial, NVS partition writer)
- [x] Web Bluetooth pairing page
- [x] Multi-user accounts with per-user API keys
- [x] AI personality + TTS streaming
- [x] Tamagotchi mechanics (needs, XP, life stages)
- [x] Achievement system
- [x] Public plant pages
- [ ] OTA firmware updates
- [ ] Push notifications (Twilio SMS / email)
- [ ] Care heatmap calendar
- [ ] 3D printed enclosure designs

---

## Science Fair

**Research question:** Can AI-driven personification of plant sensor data meaningfully improve plant care adherence compared to traditional alert-based monitoring?

**Hypothesis:** Users who receive emotionally-framed, in-character plant feedback (rather than raw threshold alerts) will water more consistently and respond faster to critical conditions.

**Metrics collected:** Watering frequency, response time to critical alerts, session engagement, self-reported care satisfaction.

---

## License

MIT — do whatever you want with it.

---

*Built with way too many debugging sessions and a plant that kept dying during development.*
