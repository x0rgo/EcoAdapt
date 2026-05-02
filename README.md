# 🌿 EcoAdapt

> A living plant companion system. Your plant monitors itself, develops a personality, and speaks to you.

![Python](https://img.shields.io/badge/Python-3.12-green?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?style=flat-square&logo=flask)
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
  └── Runs threshold checks per species
  └── Calls AI API to generate plant speech
  └── Pushes live data via WebSocket

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
- **Research-backed thresholds** — moisture, temperature and light ranges sourced from horticultural references
- **Night mode** — light alerts and energy score suppressed at night (07:00–21:00)
- **Neglect memory** — the plant remembers when it was ignored and brings it up
- **Command system** — force readings, change intervals, set modes (Demo/Normal/Eco) from the dashboard
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
| Frontend | Vanilla HTML/JS, Chart.js, Socket.IO |
| Hosting | Render.com |

---

## Project Structure

```
ecoadapt/
├── main.py           # App entry, scheduler
├── api.py            # All REST endpoints
├── ws.py             # WebSocket server
├── db.py             # SQLite interface
├── personality.py    # AI speech generation
├── thresholds.py     # Per-species care rules
├── tamagotchi.py     # Needs, happiness, XP engine
├── species.py        # Research-backed species config
├── static/
│   └── index.html    # Full web dashboard
└── requirements.txt
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- An [OpenRouter](https://openrouter.ai) API key

### Local setup

```bash
git clone https://github.com/x0rgo/EcoAdapt.git
cd EcoAdapt
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file:
```
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=mistralai/mistral-nemo
SECRET_KEY=your_secret
DEBUG=true
```

Run:
```bash
python main.py
```

Open `http://localhost:5000`

### Deploy to Render

1. Push to GitHub
2. Connect repo to [Render](https://render.com)
3. Add `OPENROUTER_API_KEY` environment variable
4. Deploy — live in ~2 minutes

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

- [ ] Bridge firmware (ESP-NOW + WiFi + offline AP)
- [ ] Pod firmware (sensors + deep sleep + command handling)
- [ ] OTA firmware updates
- [ ] Push notifications (Twilio SMS)
- [ ] Multi-plant support
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
