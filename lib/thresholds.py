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

    # ========== MOISTURE ==========
    if moisture < t["moisture_low"]:
        deficit = t["moisture_low"] - moisture
        # Estimate: 1% rise ≈ 20-30ml per liter of soil (for ~6L pot, ~120-180ml per %)
        ml_needed = deficit * 150  # middle estimate
        frequency = "Check daily until moisture is above 50%" if moisture < 30 else "Water within 24 hours"
        tips.append(f"💧 WATER NEEDED — soil is {moisture:.0f}% (need {t['moisture_low']:.0f}%+)\n"
                   f"   Add approximately {ml_needed:.0f}ml of water\n"
                   f"   {frequency}\n"
                   f"   Target: {t['moisture_low']:.0f}-{t['moisture_high']:.0f}%")
    elif moisture > t["moisture_high"]:
        excess = moisture - t["moisture_high"]
        days_to_dry = max(2, int(excess / 5))  # rough estimate: 5% per day in normal conditions
        tips.append(f"🚫 TOO WET — soil is {moisture:.0f}% (max should be {t['moisture_high']:.0f}%)\n"
                   f"   Do NOT water. Let soil dry naturally.\n"
                   f"   Check again in {days_to_dry}-{days_to_dry+1} days\n"
                   f"   Improve drainage to prevent root rot\n"
                   f"   Target: {t['moisture_low']:.0f}-{t['moisture_high']:.0f}%")
    else:
        ideal_range = t["moisture_high"] - t["moisture_low"]
        position = ((moisture - t["moisture_low"]) / ideal_range) * 100 if ideal_range > 0 else 50
        if position < 30:
            tips.append(f"✅ Moisture OK — {moisture:.0f}% (on the dry side)\n"
                       f"   Water when it drops below {t['moisture_low']:.0f}%\n"
                       f"   Target range: {t['moisture_low']:.0f}-{t['moisture_high']:.0f}%")
        elif position > 70:
            tips.append(f"✅ Moisture OK — {moisture:.0f}% (on the wet side)\n"
                       f"   Good, but watch it doesn't exceed {t['moisture_high']:.0f}%\n"
                       f"   Target range: {t['moisture_low']:.0f}-{t['moisture_high']:.0f}%")
        else:
            tips.append(f"✅ Moisture PERFECT — {moisture:.0f}% (ideal range)\n"
                       f"   Keep maintaining. Target: {t['moisture_low']:.0f}-{t['moisture_high']:.0f}%")

    # ========== TEMPERATURE ==========
    if temperature < t["temp_low"]:
        deficit = t["temp_low"] - temperature
        if temperature < -10:
            tips.append(f"🥶 CRITICAL COLD — {temperature:.1f}°C! Move inside NOW!\n"
                       f"   This is freezing. Plant will likely die if exposed longer.")
        elif temperature < 5:
            tips.append(f"🥶 SEVERE COLD — {temperature:.1f}°C\n"
                       f"   Move indoors immediately (need {deficit:.1f}°C warmer)\n"
                       f"   Place away from cold windows and drafts\n"
                       f"   Target: {t['temp_low']:.0f}-{t['temp_high']:.0f}°C")
        else:
            tips.append(f"🥶 TOO COLD — {temperature:.1f}°C (need {deficit:.1f}°C warmer)\n"
                       f"   Move to warmer location (away from AC, windows)\n"
                       f"   Consider using a heat mat (gentle warmth)\n"
                       f"   Target: {t['temp_low']:.0f}-{t['temp_high']:.0f}°C")
    elif temperature > t["temp_high"]:
        excess = temperature - t["temp_high"]
        if temperature > 40:
            tips.append(f"🌡️ EXTREME HEAT — {temperature:.1f}°C! Move immediately!\n"
                       f"   This is dangerously hot. Leaves will scorch.")
        elif temperature > 35:
            tips.append(f"🌡️ SEVERE HEAT — {temperature:.1f}°C (too hot by {excess:.1f}°C)\n"
                       f"   Move away from direct sun immediately\n"
                       f"   Increase humidity and air circulation\n"
                       f"   Water more frequently (heat dries soil faster)\n"
                       f"   Target: {t['temp_low']:.0f}-{t['temp_high']:.0f}°C")
        else:
            tips.append(f"🌡️ TOO WARM — {temperature:.1f}°C (too hot by {excess:.1f}°C)\n"
                       f"   Move away from direct sunlight\n"
                       f"   Increase air circulation (fan on low)\n"
                       f"   Mist leaves to cool them\n"
                       f"   Target: {t['temp_low']:.0f}-{t['temp_high']:.0f}°C")
    else:
        ideal_range = t["temp_high"] - t["temp_low"]
        position = ((temperature - t["temp_low"]) / ideal_range) * 100 if ideal_range > 0 else 50
        if temperature < 10:
            tips.append(f"✅ Temperature OK — {temperature:.1f}°C (slightly cool)\n"
                       f"   Growth may be slower. Ideal: {t['temp_low']:.0f}-{t['temp_high']:.0f}°C")
        else:
            tips.append(f"✅ Temperature PERFECT — {temperature:.1f}°C\n"
                       f"   Ideal range: {t['temp_low']:.0f}-{t['temp_high']:.0f}°C")

    # ========== LIGHT ==========
    if light < t["light_low"]:
        deficit = t["light_low"] - light
        tips.append(f"☀️ TOO DARK — {light:.0f} lux (need {t['light_low']:.0f}+ lux)\n"
                   f"   Move to brighter location:\n"
                   f"   • South/west-facing window preferred\n"
                   f"   • Avoid heavy curtains/obstacles\n"
                   f"   • Consider grow light if relocation impossible\n"
                   f"   • Bright indirect light is best\n"
                   f"   Target: {t['light_low']:.0f}-{t['light_high']:.0f} lux")
    elif light > t["light_high"]:
        excess = light - t["light_high"]
        if light > 30000:
            tips.append(f"🌤️ SCORCHING LIGHT — {light:.0f} lux (too much direct sun)\n"
                       f"   Move back from window or use sheer curtain\n"
                       f"   Leaves may bleach/burn if exposed\n"
                       f"   Increase watering (intense light dries soil)\n"
                       f"   Target: {t['light_low']:.0f}-{t['light_high']:.0f} lux")
        else:
            tips.append(f"🌤️ TOO BRIGHT — {light:.0f} lux (excess by {excess:.0f})\n"
                       f"   Move back from window or add sheer curtain\n"
                       f"   Direct afternoon sun can damage leaves\n"
                       f"   Target: {t['light_low']:.0f}-{t['light_high']:.0f} lux")
    else:
        if light < 1000:
            tips.append(f"✅ Light OK — {light:.0f} lux (bright indirect)\n"
                       f"   Good for most plants. Ideal: {t['light_low']:.0f}-{t['light_high']:.0f} lux")
        elif light > 20000:
            tips.append(f"✅ Light EXCELLENT — {light:.0f} lux (very bright)\n"
                       f"   Ideal for high-light plants. Range: {t['light_low']:.0f}-{t['light_high']:.0f} lux")
        else:
            tips.append(f"✅ Light PERFECT — {light:.0f} lux\n"
                       f"   Ideal range: {t['light_low']:.0f}-{t['light_high']:.0f} lux")

    return tips
