"""
tamagotchi.py — EcoAdapt needs, happiness, XP and life stage engine

Needs (0-100 each):
  thirst   — inverse of moisture. Low moisture = high thirst
  energy   — based on light level vs species ideal
  comfort  — based on temperature vs species ideal

Happiness (0-100):
  Composite of needs. Drops when needs are unmet, rises when cared for.
  Decays slowly over time if no readings come in.

XP:
  Awarded for care actions detected from sensor data.
  Accumulates toward life stage progression.

Life stages (0-4):
  0 🌰 Seed      — just starting out, shy and quiet
  1 🌱 Sprout    — beginning to open up
  2 🪴 Seedling  — developing personality
  3 🌿 Plant     — fully expressive
  4 🌳 Thriving  — maximum personality, unlocks special dialogue
"""

from datetime import datetime, timedelta
from db import get_plant, save_plant, get_latest, get_history, get_db
from species import get_species
from datetime import datetime

def _is_daytime():
    hour = datetime.now().hour
    return 7 <= hour <= 21

# ─────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────

STAGES = [
    { "id": 0, "name": "Seed",     "emoji": "🌰", "xp_required": 0,    "desc": "Just starting out." },
    { "id": 1, "name": "Sprout",   "emoji": "🌱", "xp_required": 100,  "desc": "Beginning to grow." },
    { "id": 2, "name": "Seedling", "emoji": "🪴", "xp_required": 300,  "desc": "Developing character." },
    { "id": 3, "name": "Plant",    "emoji": "🌿", "xp_required": 700,  "desc": "Fully expressive." },
    { "id": 4, "name": "Thriving", "emoji": "🌳", "xp_required": 1500, "desc": "Peak vitality." },
]

# XP awards
XP_WATERED_IN_TIME   = 20   # watered before moisture hit critical
XP_WATERED_CRITICAL  = 8    # watered but only after critical
XP_GOOD_LIGHT_HOUR   = 2    # per hour of good light
XP_GOOD_TEMP_HOUR    = 1    # per hour of good temp
XP_CHAT_INTERACTION  = 3    # per chat message
XP_DAILY_CHECKIN     = 5    # daily checkin completed

# Happiness decay per hour with no readings
HAPPINESS_DECAY_PER_HOUR = 2.0

# Happiness change rates
HAPPINESS_GAIN_PER_GOOD_READING  = 3.0
HAPPINESS_LOSS_PER_BAD_READING   = 4.0
HAPPINESS_CRITICAL_PENALTY       = 10.0

# ─────────────────────────────────────────────────────────
# NEEDS CALCULATION
# ─────────────────────────────────────────────────────────

def calculate_needs(reading, species_name):
    config = get_species(species_name)
    t = config["thresholds"]

    moisture    = reading.get("moisture", 50)
    temperature = reading.get("temperature", 20)
    light       = reading.get("light", 1000)

    # Thirst
    moisture_range = t["moisture_high"] - t["moisture_low"]
    thirst = ((moisture - t["moisture_low"]) / moisture_range) * 100
    thirst = max(0, min(100, thirst))

    # Energy — always 100 at night, plants rest
    if _is_daytime():
        light_mid   = (t["light_low"] + t["light_high"]) / 2
        light_range = (t["light_high"] - t["light_low"]) / 2
        energy = max(0, 100 - abs(light - light_mid) / light_range * 100)
        energy = max(0, min(100, energy))
    else:
        energy = 100

    # Comfort
    temp_mid   = (t["temp_low"] + t["temp_high"]) / 2
    temp_range = (t["temp_high"] - t["temp_low"]) / 2
    comfort = max(0, 100 - abs(temperature - temp_mid) / temp_range * 100)
    comfort = max(0, min(100, comfort))

    return {
        "thirst":  round(thirst, 1),
        "energy":  round(energy, 1),
        "comfort": round(comfort, 1),
    }
    
def calculate_happiness(needs):
    """
    Weighted composite of needs.
    Thirst is most important (50%), energy (30%), comfort (20%).
    """
    h = (
        needs["thirst"]  * 0.50 +
        needs["energy"]  * 0.30 +
        needs["comfort"] * 0.20
    )
    return round(h, 1)

def get_mood_from_happiness(happiness):
    if happiness >= 80: return "happy"
    if happiness >= 60: return "content"
    if happiness >= 40: return "uneasy"
    if happiness >= 20: return "distressed"
    return "critical"

# ─────────────────────────────────────────────────────────
# LIFE STAGE
# ─────────────────────────────────────────────────────────

def get_stage(xp):
    current = STAGES[0]
    for stage in STAGES:
        if xp >= stage["xp_required"]:
            current = stage
    return current

def get_next_stage(xp):
    for stage in STAGES:
        if xp < stage["xp_required"]:
            return stage
    return None  # already at max

def xp_progress(xp):
    """Returns 0-100 progress to next stage."""
    current = get_stage(xp)
    next_s  = get_next_stage(xp)
    if not next_s:
        return 100
    progress_in_stage = xp - current["xp_required"]
    stage_size        = next_s["xp_required"] - current["xp_required"]
    return round((progress_in_stage / stage_size) * 100, 1)

# ─────────────────────────────────────────────────────────
# CARE ACTION DETECTION
# ─────────────────────────────────────────────────────────

def detect_watering(current_reading, previous_reading, species_name):
    """
    Detects if the plant was watered between two readings.
    Returns XP to award and whether it was timely.
    """
    if not previous_reading:
        return 0, False

    config   = get_species(species_name)
    t        = config["thresholds"]
    prev_m   = previous_reading.get("moisture", 50)
    curr_m   = current_reading.get("moisture", 50)

    # Moisture jumped up significantly
    if curr_m - prev_m > 15:
        was_critical = prev_m < t["moisture_low"]
        xp = XP_WATERED_CRITICAL if was_critical else XP_WATERED_IN_TIME
        return xp, not was_critical

    return 0, False

# ─────────────────────────────────────────────────────────
# MAIN UPDATE — called on every new reading
# ─────────────────────────────────────────────────────────

def update_tamagotchi(reading, user_id=1):
    plant        = get_plant(user_id)
    species_name = plant.get("species", "pothos")

    happiness = float(plant.get("happiness", 100))
    xp        = float(plant.get("xp", 0))

    needs = calculate_needs(reading, species_name)
    new_happiness = calculate_happiness(needs)
    happiness = happiness * 0.7 + new_happiness * 0.3
    happiness = max(0, min(100, happiness))

    history   = get_history(hours=1, user_id=user_id)
    prev      = history[-2] if len(history) >= 2 else None
    xp_gained, timely = detect_watering(reading, prev, species_name)

    if xp_gained:
        xp += xp_gained
        _store_care_action("watered", xp_gained, timely, user_id)

    if needs["thirst"]  > 60: xp += 0.5
    if needs["energy"]  > 60: xp += 0.3
    if needs["comfort"] > 60: xp += 0.2

    stage = get_stage(xp)

    save_plant({
        "happiness": round(happiness, 1),
        "xp":        round(xp, 1),
        "stage":     stage["id"],
    }, user_id)

    return build_state(reading, needs, happiness, xp, stage, species_name)

def award_xp(amount, reason="interaction"):
    """Award XP for non-sensor actions like chatting."""
    plant = get_plant()
    xp    = float(plant.get("xp", 0)) + amount
    stage = get_stage(xp)
    save_plant({"xp": round(xp, 1), "stage": stage["id"]})
    return xp

# ─────────────────────────────────────────────────────────
# STATE BUILDER
# ─────────────────────────────────────────────────────────

def build_state(reading=None, needs=None, happiness=None, xp=None, stage=None, species_name=None, user_id=1):
    plant = get_plant(user_id)
    if reading is None:
        reading = get_latest(user_id=user_id) or {"moisture": 50, "temperature": 20, "light": 5000, "battery": 100}

    species_name = species_name or plant.get("species", "pothos")

    if needs is None:
        needs = calculate_needs(reading, species_name)

    if happiness is None:
        happiness = float(plant.get("happiness", 100))

    if xp is None:
        xp = float(plant.get("xp", 0))

    if stage is None:
        stage = get_stage(xp)

    next_stage = get_next_stage(xp)
    mood       = get_mood_from_happiness(happiness)

    return {
        "needs":      needs,
        "happiness":  round(happiness, 1),
        "mood":       mood,
        "xp":         round(xp, 1),
        "stage":      stage,
        "next_stage": next_stage,
        "xp_progress": xp_progress(xp),
        "stages":     STAGES,
    }

def get_state(user_id=1):
    return build_state(user_id=user_id)


# ─────────────────────────────────────────────────────────
# CARE ACTION LOG
# ─────────────────────────────────────────────────────────

def _store_care_action(action, xp, timely, user_id=1):
    conn = get_db()
    conn.execute(
        "INSERT INTO care_log (action, xp_awarded, timely, user_id) VALUES (?,?,?,?)",
        (action, xp, 1 if timely else 0, user_id)
    )
    conn.commit()
    conn.close()

def get_care_log(limit=50):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM care_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    except:
        return []
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────
# NEGLECT DETECTION
# ─────────────────────────────────────────────────────────

def get_neglect_summary():
    """
    Returns a summary of neglect for the personality engine.
    Used to make the plant remember being neglected.
    """
    plant     = get_plant()
    happiness = float(plant.get("happiness", 100))
    history   = get_history(hours=72)  # last 3 days

    if not history:
        return None

    # Count hours of critical moisture
    species_name = plant.get("species", "pothos")
    config       = get_species(species_name)
    t            = config["thresholds"]

    critical_readings = [r for r in history if r["moisture"] < t["moisture_low"]]
    critical_hours    = len(critical_readings) * 5 / 60  # assuming 5min intervals

    neglect = {
        "happiness":       happiness,
        "critical_hours":  round(critical_hours, 1),
        "was_neglected":   critical_hours > 2,
        "severely":        critical_hours > 12,
    }

    return neglect
