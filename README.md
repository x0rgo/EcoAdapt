# 🌿 EcoAdapt

> A living plant companion system. Your plant monitors itself, develops a personality, and speaks to you.

![Python](https://img.shields.io/badge/Python-3.12-green?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey?style=flat-square&logo=flask)
![Arduino](https://img.shields.io/badge/Arduino-ESP32-teal?style=flat-square&logo=arduino)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

---

## What is EcoAdapt?

EcoAdapt is an AI-powered plant monitoring system that turns your houseplant into a Tamagotchi-style companion. Real soil sensors feed live data to a cloud server, which uses AI to generate in-character speech based on your plant's mood, needs, and life stage.

The plant grows over time, remembers neglect, reacts to its environment, and talks to you through a web dashboard and browser TTS.

---

## How it works

```
Sensor Pod (XIAO C3 #1)
  └── Soil moisture, temperature, light
  └── Deep sleep between readings (months of battery life)
  └── Transmits via ESP-NOW →

Bridge (XIAO C3 #2)
  └── Always on, plugged in
  └── Receives ESP-NOW packets
  └── Forwards to cloud server via WiFi (phone hotspot)
  └── Falls back to local AP + dashboard if no WiFi

Cloud Server (Render / Flask)
  └── Stores all sensor readings in SQLite
  └── Handles accounts, sessions, and pod API keys
  └── Runs threshold checks per species
  └── Calls AI API to generate plant speech
  └── Pushes live data via WebSocket
  └── Serves firmware flashing and pairing pages

Web Dashboard
  └── Live sensor gauges
  └── Tamagotchi pet panel (needs, happiness, XP, life stages)
  └── Chat directly with your plant
  └── History charts
  └── Plant settings and pod control
```

---

## Features

- **AI personality** — each plant species has a distinct character (dramatic peace lily, stoic cactus, anxious fern...)
- **Tamagotchi mechanics** — needs system, happiness score, XP, 5 life stages
- **Achievements** — unlockable milestones for care, interaction, growth, neglect and chaos
- **Accounts + API keys** — user login with per-user pod pairing credentials
- **Research-backed thresholds** — moisture, temperature and light ranges sourced from horticultural references
- **Night mode** — light alerts and energy score suppressed at night (07:00–21:00)
- **Neglect memory** — the plant remembers when it was ignored and brings it up
- **Command system** — force readings, change intervals, set modes (Demo/Normal/Eco) from the dashboard
- **Browser speech** — generated TTS audio and streaming speech endpoints
- **Web flasher** — browser-based firmware flashing and pod pairing pages
- **Offline fallback** — bridge broadcasts its own WiFi hotspot with a backup dashboard when internet is unavailable
- **Model selector** — swap AI models (Mistral, Claude, Gemini, Llama) from the settings panel

---

## Hardware

| Component | Purpose |
|---|---|
| Seeed XIAO ESP32C3 × 2 | Sensor pod + WiFi bridge |
| HW-390 capacitive moisture sensor | Soil moisture |
| DS18B20 waterproof probe | Soil temperature |
| Adafruit VEML7700 | Ambient light (lux) |
| 1200mAh LiPo battery | Pod power (~6 months per charge) |
| Raspberry Pi 3B+ (optional) | Local development / speaker output |

---

## Software Stack

| Layer | Tech |
|---|---|
| Pod + Bridge firmware | Arduino C++ (ESP-IDF) |
| Backend | Python 3.12, Flask, Flask-SocketIO |
| Database | SQLite |
| AI | OpenRouter API (Mistral Nemo default) |
| TTS | OpenRouter speech models |
| Frontend | Vanilla HTML/JS, Chart.js, Socket.IO |
| Hosting | Render.com |

---

## Project Structure

```text
EcoAdapt/
├── main.py                    # Flask app entrypoint and scheduler
├── requirements.txt           # Python dependencies
├── render.yaml                # Render deployment config
├── lib/                       # Application package
│   ├── __init__.py
│   ├── api.py                 # REST API routes
│   ├── auth.py                # Login, sessions, API keys
│   ├── db.py                  # SQLite schema and data access
│   ├── ws.py                  # Socket.IO events
│   ├── flash_routes.py        # Firmware flashing/pairing backend
│   ├── personality.py         # AI plant dialogue
│   ├── tts.py                 # Speech generation helpers
│   ├── thresholds.py          # Care checks and recommendations
│   ├── tamagotchi.py          # Needs, happiness, XP, life stages
│   ├── achievements.py        # Achievement unlock logic
│   └── species.py             # Species-specific care profiles
├── static/
│   ├── index.html             # Main dashboard
│   ├── flash.html             # Web firmware flasher
│   └── pair.html              # Browser pod pairing page
├── firmware/
│   ├── bridge/                # Bridge firmware source
│   ├── pod/                   # Sensor pod firmware source
│   └── build_scripts/         # Firmware build helpers
├── ecoadapt-firmware/         # Firmware flasher integration files
└── instance/firmware/         # Built firmware binaries at runtime
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- An [OpenRouter](https://openrouter.ai) API key
- ESP32-C3 hardware if you are flashing real pods/bridges

### Local setup

```bash
git clone https://github.com/x0rgo/EcoAdapt.git
cd EcoAdapt
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:
```
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=mistralai/mistral-nemo
SECRET_KEY=your_secret
DEBUG=true
DB_PATH=ecoadapt.db
```

Run:
```bash
python main.py
```

Open `http://localhost:5000`

The app loads `main.py` from the repo root. Internal application code is imported from the `lib` package.

### Firmware binaries

The web flasher expects built firmware files under `instance/firmware/`:

```text
instance/firmware/bridge.bin
instance/firmware/pod.bin
instance/firmware/bootloader.bin
instance/firmware/partitions.bin
```

Firmware source lives in `firmware/bridge` and `firmware/pod`. Build helpers live in `firmware/build_scripts`.

### Deploy to Render

The included `render.yaml` runs:

```bash
pip install -r requirements.txt
python main.py
```

It also configures a persistent disk at `/data` and sets `DB_PATH=/data/ecoadapt.db`.

1. Push to GitHub
2. Connect repo to [Render](https://render.com)
3. Add `OPENROUTER_API_KEY` as a secret environment variable
4. Deploy

---

## Species Threshold Sources

All plant care thresholds are research-backed:

| Parameter | Source |
|---|---|
| Soil moisture | [Elm Dirt Moisture Meter Guide](https://www.elmdirt.com/blogs/news/moisture-meter-guide) |
| Light levels (lux) | [Wikiversity Houseplant Care](https://en.wikiversity.org/wiki/Houseplant_care) + [House Plant Journal](https://www.houseplantjournal.com) |
| Temperature ranges | [Cielo Blog](https://cielowigle.com/blog/temperature-for-plants/) + [University of Arkansas Extension](https://www.uaex.uada.edu/yard-garden/home-landscape/docs/Temperature%20Requirements%20of%20Selected%20House%20Plants.pdf) |
| Cactus/succulent temps | [Cactus & Succulent Society of MA](https://www.cssma.org/succulent-care) |

---

## Roadmap

- [x] Bridge firmware (ESP-NOW + WiFi + offline AP)
- [x] Pod firmware (sensors + deep sleep + command handling)
- [ ] OTA firmware updates
- [ ] Push notifications (Twilio SMS)
- [x](Sort of, not really tested properly but should work in theory) Multi-plant support
- [ ] Care heatmap calendar
- [ ] 3D printed enclosure

---

## Science Fair

This project was developed as a science fair entry exploring the intersection of IoT sensor systems, AI personality generation, and behavioral gamification in plant care.

**Research question:** Can AI-driven personification of plant sensor data meaningfully improve plant care adherence compared to traditional alert-based monitoring systems?

---

## License

MIT — do whatever you want with it.

---

*Built with 🌱 and way too many debugging sessions.*
