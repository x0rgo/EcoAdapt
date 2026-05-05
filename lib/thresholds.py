from lib.species import get_species
from lib.db import get_latest, get_utterances
from datetime import datetime, timedelta
from datetime import datetime
def _is_daytime():
    hour = datetime.now().hour
    return 7 <= hour <= 21

# Minimum minutes between same alert type to avoid spamming
DEBOUNCE_MINUTES = 30

def _last_utterance_time(trigger_type):
    utterances = get_utterances(limit=20)
    for u in utterances:
        if u["trigger"] == trigger_type:
            ts = datetime.fromisoformat(u["timestamp"])
            return ts
    return None

def _should_speak(trigger_type):
    last = _last_utterance_time(trigger_type)
    if last is None:
        return True
    return datetime.utcnow() - last > timedelta(minutes=DEBOUNCE_MINUTES)

def get_mood(reading, species_name):
    config = get_species(species_name)
    t = config["thresholds"]
    moisture = reading.get("moisture", 50)
    temperature = reading.get("temperature", 20)
    light = reading.get("light", 1000)

    if moisture < t["moisture_low"]:
        return "thirsty"
    if moisture > t["moisture_high"]:
        return "overwatered"
    if temperature < t["temp_low"]:
        return "cold"
    if temperature > t["temp_high"]:
        return "hot"
    if light < t["light_low"]:
        return "dim"
    if light > t["light_high"]:
        return "bright"
    return "happy"

def check_reading(reading, species_name):
    config = get_species(species_name)
    t = config["thresholds"]
    triggers = []

    moisture = reading.get("moisture", 50)
    temperature = reading.get("temperature", 20)
    light = reading.get("light", 1000)
    battery = reading.get("battery", 100)

    if moisture < t["moisture_low"] and _should_speak("moisture_low"):
        triggers.append({
            "type": "moisture_low",
            "message": f"Moisture is very low at {moisture:.0f}%",
            "mood": "thirsty"
        })

    elif moisture > t["moisture_high"] and _should_speak("moisture_high"):
        triggers.append({
            "type": "moisture_high",
            "message": f"Moisture is very high at {moisture:.0f}%",
            "mood": "overwatered"
        })

    if temperature < t["temp_low"] and _should_speak("temp_low"):
        triggers.append({
            "type": "temp_low",
            "message": f"Temperature is low at {temperature:.1f}°C",
            "mood": "cold"
        })

    elif temperature > t["temp_high"] and _should_speak("temp_high"):
        triggers.append({
            "type": "temp_high",
            "message": f"Temperature is high at {temperature:.1f}°C",
            "mood": "hot"
        })
    if _is_daytime():
        if light < t["light_low"] and _should_speak("light_low"):
            triggers.append({
                "type": "light_low",
                "message": f"Light is low at {light:.0f} lux",
                "mood": "dim"
            })

        elif light > t["light_high"] and _should_speak("light_high"):
            triggers.append({
                "type": "light_high",
                "message": f"Light is very high at {light:.0f} lux",
                "mood": "bright"
            })

    if battery < 20 and _should_speak("battery_low"):
        triggers.append({
            "type": "battery_low",
            "message": f"Pod battery is low at {battery:.0f}%",
            "mood": "neutral"
        })

    return triggers

def get_recommendations(reading, species_name):
    config = get_species(species_name)
    t = config["thresholds"]
    tips = []

    moisture = reading.get("moisture", 50)
    temperature = reading.get("temperature", 20)
    light = reading.get("light", 1000)

    if moisture < t["moisture_low"]:
        tips.append("💧 Water your plant — soil moisture is too low")
    elif moisture > t["moisture_high"]:
        tips.append("🚫 Hold off watering — soil is too wet")
    else:
        tips.append("✅ Moisture level is good")

    if temperature < t["temp_low"]:
        if temperature < -10:
            tips.append(f"🥶 HOLY CRAP WHERE ARE YOU? — current temp is {temperature:.1f}°C")
        else:
            tips.append(f"🥶 Move somewhere warmer — current temp is {temperature:.1f}°C")
    elif temperature > t["temp_high"]:
        tips.append(f"🌡️ Too warm — move away from heat sources")
    else:
        tips.append("✅ Temperature is comfortable")

    if light < t["light_low"]:
        tips.append("☀️ Move to a brighter spot — light is too low")
    elif light > t["light_high"]:
        tips.append("🌤️ Too much direct light — consider moving back")
    else:
        tips.append("✅ Light level is good")

    return tips
