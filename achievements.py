"""
achievements.py — EcoAdapt achievement system

Achievements are checked after every sensor reading and after
key user interactions. Unlocked achievements are stored in the
DB and never re-awarded.
"""

from datetime import datetime, timedelta
from db import get_db, get_plant, get_latest, get_history, get_chat_history

# ─────────────────────────────────────────────────────────
# ACHIEVEMENT DEFINITIONS
# ─────────────────────────────────────────────────────────

ACHIEVEMENTS = {
    # Care-based
    "first_drink": {
        "id": "first_drink",
        "name": "First Drink",
        "emoji": "💧",
        "desc": "Moisture recovered from low for the first time.",
        "category": "care",
        "xp": 10,
    },
    "on_time": {
        "id": "on_time",
        "name": "On Time",
        "emoji": "⏱️",
        "desc": "Watered before hitting critical 5 times.",
        "category": "care",
        "xp": 25,
    },
    "week_streak": {
        "id": "week_streak",
        "name": "Week Streak",
        "emoji": "🌿",
        "desc": "7 days of healthy moisture levels.",
        "category": "care",
        "xp": 50,
    },
    "sun_seeker": {
        "id": "sun_seeker",
        "name": "Sun Seeker",
        "emoji": "☀️",
        "desc": "Good light levels maintained for 24 hours straight.",
        "category": "care",
        "xp": 20,
    },

    # Interaction
    "first_words": {
        "id": "first_words",
        "name": "First Words",
        "emoji": "💬",
        "desc": "Sent your first chat message to the plant.",
        "category": "interaction",
        "xp": 5,
    },
    "chatterbox": {
        "id": "chatterbox",
        "name": "Chatterbox",
        "emoji": "🗣️",
        "desc": "Sent 50 chat messages.",
        "category": "interaction",
        "xp": 30,
    },
    "name_giver": {
        "id": "name_giver",
        "name": "Name Giver",
        "emoji": "🏷️",
        "desc": "Gave your plant a name.",
        "category": "interaction",
        "xp": 10,
    },
    "method_actor": {
        "id": "method_actor",
        "name": "Method Actor",
        "emoji": "🎭",
        "desc": "Tried all 7 plant species personalities.",
        "category": "interaction",
        "xp": 40,
    },
    "night_owl": {
        "id": "night_owl",
        "name": "Night Owl",
        "emoji": "🌙",
        "desc": "Chatted with your plant between 2am and 4am.",
        "category": "interaction",
        "xp": 15,
    },
    "philosopher": {
        "id": "philosopher",
        "name": "Philosopher",
        "emoji": "🤖",
        "desc": "Sent a message over 200 characters long.",
        "category": "interaction",
        "xp": 10,
    },
    "polyglot": {
        "id": "polyglot",
        "name": "Polyglot",
        "emoji": "🌍",
        "desc": "Changed plant species 5 times.",
        "category": "interaction",
        "xp": 20,
    },

    # Growth
    "sprouted": {
        "id": "sprouted",
        "name": "Sprouted",
        "emoji": "🌱",
        "desc": "Reached the Sprout life stage.",
        "category": "growth",
        "xp": 0,  # XP awarded by reaching stage itself
    },
    "thriving_stage": {
        "id": "thriving_stage",
        "name": "Thriving",
        "emoji": "🌳",
        "desc": "Reached the maximum life stage.",
        "category": "growth",
        "xp": 0,
    },
    "century": {
        "id": "century",
        "name": "Century",
        "emoji": "⭐",
        "desc": "Accumulated 100 XP.",
        "category": "growth",
        "xp": 0,
    },

    # Neglect / recovery
    "close_call": {
        "id": "close_call",
        "name": "Close Call",
        "emoji": "😰",
        "desc": "Plant hit critical moisture but recovered.",
        "category": "neglect",
        "xp": 5,
    },
    "comeback": {
        "id": "comeback",
        "name": "Comeback",
        "emoji": "🏥",
        "desc": "Happiness dropped below 20 then recovered above 80.",
        "category": "neglect",
        "xp": 15,
    },

    # Extreme / fun
    "absolute_zero": {
        "id": "absolute_zero",
        "name": "Absolute Zero",
        "emoji": "🥶",
        "desc": "Uhm? Is your plant okay? Soil temperature dropped below 0°C.",
        "category": "extreme",
        "xp": 20,
    },
    "volcano": {
        "id": "volcano",
        "name": "Volcano",
        "emoji": "🌋",
        "desc": "Wow okay, you might be an arsonist... Soil temperature exceeded 45°C.",
        "category": "extreme",
        "xp": 20,
    },
    "surface_of_sun": {
        "id": "surface_of_sun",
        "name": "Surface of the Sun",
        "emoji": "🔆",
        "desc": "Light reading exceeded 50,000 lux.",
        "category": "extreme",
        "xp": 25,
    },
    
    "void": {
        "id": "void",
        "name": "The Void",
        "emoji": "👁️",
        "desc": "Recorded a 0 lux reading — complete darkness.",
        "category": "extreme",
        "xp": 15,
    },
    "brink": {
        "id": "brink",
        "name": "The Brink",
        "emoji": "💀",
        "desc": "Soil moisture hit 0%.",
        "category": "extreme",
        "xp": 10,
    },
    "atlantis": {
        "id": "atlantis",
        "name": "Atlantis",
        "emoji": "🌊",
        "desc": "Soil moisture hit 100%.",
        "category": "extreme",
        "xp": 10,
    },
    "flatliner": {
        "id": "flatliner",
        "name": "Flatliner",
        "emoji": "🔋",
        "desc": "Pod battery hit 0%.",
        "category": "extreme",
        "xp": 10,
    },
    "ghost_plant": {
        "id": "ghost_plant",
        "name": "Ghost Plant",
        "emoji": "👻",
        "desc": "No readings for 7 days, then one arrived.",
        "category": "extreme",
        "xp": 15,
    },

    # Birthday milestones
    "two_weeks": {
        "id": "two_weeks",
        "name": "Two Weeks",
        "emoji": "🎂",
        "desc": "Your plant has been alive for 15 days.",
        "category": "birthday",
        "xp": 20,
    },
    "one_month": {
        "id": "one_month",
        "name": "One Month",
        "emoji": "🎉",
        "desc": "Your plant has been alive for 30 days.",
        "category": "birthday",
        "xp": 30,
    },
    "sixty_days": {
        "id": "sixty_days",
        "name": "Thriving",
        "emoji": "🌿",
        "desc": "Your plant has been alive for 60 days.",
        "category": "birthday",
        "xp": 40,
    },
    "survivor": {
        "id": "survivor",
        "name": "Survivor",
        "emoji": "💪",
        "desc": "Your plant has been alive for 100 days.",
        "category": "birthday",
        "xp": 50,
    },
    "veteran": {
        "id": "veteran",
        "name": "Veteran",
        "emoji": "🏆",
        "desc": "Your plant has been alive for 180 days.",
        "category": "birthday",
        "xp": 75,
    },
    "ancient": {
        "id": "ancient",
        "name": "Ancient",
        "emoji": "🌳",
        "desc": "Your plant has been alive for 365 days.",
        "category": "birthday",
        "xp": 100,
    },
    "legend": {
        "id": "legend",
        "name": "Legend",
        "emoji": "👑",
        "desc": "Your plant has been alive for 730 days.",
        "category": "birthday",
        "xp": 200,
    },
}

# ─────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────

def init_achievements_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id          TEXT PRIMARY KEY,
            unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievement_counters (
            key   TEXT PRIMARY KEY,
            value INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def is_unlocked(achievement_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM achievements WHERE id=?", (achievement_id,)
    ).fetchone()
    conn.close()
    return row is not None

def unlock(achievement_id):
    """Unlock an achievement. Returns True if newly unlocked, False if already had it."""
    if is_unlocked(achievement_id):
        return False
    conn = get_db()
    conn.execute(
        "INSERT INTO achievements (id) VALUES (?)", (achievement_id,)
    )
    conn.commit()
    conn.close()
    return True

def get_counter(key):
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM achievement_counters WHERE key=?", (key,)
    ).fetchone()
    conn.close()
    return row["value"] if row else 0

def increment_counter(key, amount=1):
    conn = get_db()
    conn.execute("""
        INSERT INTO achievement_counters (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = value + ?
    """, (key, amount, amount))
    conn.commit()
    conn.close()
    return get_counter(key)

def set_counter(key, value):
    conn = get_db()
    conn.execute("""
        INSERT INTO achievement_counters (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = ?
    """, (key, value, value))
    conn.commit()
    conn.close()

def get_all_unlocked():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, unlocked_at FROM achievements ORDER BY unlocked_at DESC"
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        ach = ACHIEVEMENTS.get(row["id"])
        if ach:
            result.append({**ach, "unlocked_at": row["unlocked_at"]})
    return result

def get_all_achievements():
    """Returns all achievements with unlock status."""
    unlocked = {r["id"]: r["unlocked_at"] for r in _get_raw_unlocked()}
    result = []
    for ach_id, ach in ACHIEVEMENTS.items():
        result.append({
            **ach,
            "unlocked": ach_id in unlocked,
            "unlocked_at": unlocked.get(ach_id)
        })
    return result

def _get_raw_unlocked():
    conn = get_db()
    rows = conn.execute("SELECT id, unlocked_at FROM achievements").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────────────────
# FIRST READING TIMESTAMP
# ─────────────────────────────────────────────────────────

def get_first_reading_date():
    conn = get_db()
    row = conn.execute(
        "SELECT timestamp FROM readings ORDER BY timestamp ASC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return datetime.fromisoformat(row["timestamp"])
    return None

# ─────────────────────────────────────────────────────────
# MAIN CHECK — called after every reading
# ─────────────────────────────────────────────────────────

def check_sensor_achievements(reading, prev_reading=None):
    """Check all sensor-based achievements. Returns list of newly unlocked."""
    newly_unlocked = []

    moisture    = reading.get("moisture", 50)
    temperature = reading.get("temperature", 20)
    light       = reading.get("light", 1000)
    battery     = reading.get("battery", 100)

    plant     = get_plant()
    happiness = float(plant.get("happiness", 100))
    xp        = float(plant.get("xp", 0))
    stage     = int(plant.get("stage", 0))

    # ── Extreme readings ──
    if temperature < 0:
        if unlock("absolute_zero"): newly_unlocked.append("absolute_zero")

    if temperature > 45:
        if unlock("volcano"): newly_unlocked.append("volcano")

    if light >= 50000:
        if unlock("surface_of_sun"): newly_unlocked.append("surface_of_sun")

    if light == 0:
        if unlock("void"): newly_unlocked.append("void")

    if moisture <= 0:
        if unlock("brink"): newly_unlocked.append("brink")

    if moisture >= 100:
        if unlock("atlantis"): newly_unlocked.append("atlantis")

    if battery <= 0:
        if unlock("flatliner"): newly_unlocked.append("flatliner")

    # ── Watering detection ──
    if prev_reading:
        prev_m = prev_reading.get("moisture", 50)
        if moisture - prev_m > 15:
            # Watering detected
            if unlock("first_drink"): newly_unlocked.append("first_drink")

            # Was it timely?
            from species import get_species
            config = get_species(plant.get("species", "pothos"))
            t = config["thresholds"]
            if prev_m > t["moisture_low"]:
                count = increment_counter("timely_waterings")
                if count >= 5 and unlock("on_time"):
                    newly_unlocked.append("on_time")

            # Was it a close call recovery?
            if prev_m < t["moisture_low"]:
                if unlock("close_call"): newly_unlocked.append("close_call")

    # ── Happiness comeback ──
    prev_happiness = get_counter("min_happiness_seen")
    if happiness < 20:
        set_counter("min_happiness_seen", int(happiness))
    elif happiness > 80 and get_counter("min_happiness_seen") < 20:
        if unlock("comeback"): newly_unlocked.append("comeback")
        set_counter("min_happiness_seen", 100)  # reset

    # ── XP milestone ──
    if xp >= 100 and unlock("century"):
        newly_unlocked.append("century")

    # ── Life stage ──
    if stage >= 1 and unlock("sprouted"):
        newly_unlocked.append("sprouted")
    if stage >= 4 and unlock("thriving_stage"):
        newly_unlocked.append("thriving_stage")

    # ── Ghost plant ──
    history = get_history(hours=168)  # 7 days
    if len(history) >= 2:
        last = datetime.fromisoformat(history[-1]["timestamp"])
        second_last = datetime.fromisoformat(history[-2]["timestamp"])
        gap = last - second_last
        if gap.total_seconds() > 7 * 24 * 3600:
            if unlock("ghost_plant"): newly_unlocked.append("ghost_plant")

    # ── Birthday milestones ──
    first = get_first_reading_date()
    if first:
        days_alive = (datetime.utcnow() - first).days
        milestones = [
            (15,  "two_weeks"),
            (30,  "one_month"),
            (60,  "sixty_days"),
            (100, "survivor"),
            (180, "veteran"),
            (365, "ancient"),
            (730, "legend"),
        ]
        for days, ach_id in milestones:
            if days_alive >= days and unlock(ach_id):
                newly_unlocked.append(ach_id)

    # ── Week streak ──
    history_7d = get_history(hours=168)
    if len(history_7d) > 0:
        from species import get_species
        config = get_species(plant.get("species", "pothos"))
        t = config["thresholds"]
        all_healthy = all(
            t["moisture_low"] <= r["moisture"] <= t["moisture_high"]
            for r in history_7d
        )
        if all_healthy and len(history_7d) >= 288:  # ~288 readings at 5min = 24h*12*7days... adjust
            if unlock("week_streak"): newly_unlocked.append("week_streak")

    # ── Sun seeker — 24h good light ──
    history_24h = get_history(hours=24)
    if len(history_24h) > 0:
        from species import get_species
        config = get_species(plant.get("species", "pothos"))
        t = config["thresholds"]
        daytime = [r for r in history_24h if 7 <= datetime.fromisoformat(r["timestamp"]).hour <= 21]
        if daytime and all(r["light"] >= t["light_low"] for r in daytime):
            if unlock("sun_seeker"): newly_unlocked.append("sun_seeker")

    return newly_unlocked


def check_interaction_achievements(interaction_type, data=None):
    """
    Check interaction-based achievements.
    interaction_type: "chat", "name_given", "species_changed", "night_chat", "long_message"
    Returns list of newly unlocked achievement IDs.
    """
    newly_unlocked = []

    if interaction_type == "chat":
        count = increment_counter("chat_messages")
        if count == 1 and unlock("first_words"):
            newly_unlocked.append("first_words")
        if count >= 50 and unlock("chatterbox"):
            newly_unlocked.append("chatterbox")

        # Night owl
        if 2 <= datetime.now().hour < 4:
            if unlock("night_owl"): newly_unlocked.append("night_owl")

        # Philosopher
        if data and len(data.get("message", "")) > 200:
            if unlock("philosopher"): newly_unlocked.append("philosopher")

    if interaction_type == "name_given":
        if unlock("name_giver"): newly_unlocked.append("name_giver")

    if interaction_type == "species_changed":
        count = increment_counter("species_changes")
        if count >= 5 and unlock("polyglot"):
            newly_unlocked.append("polyglot")

        # Track unique species tried
        if data and "species" in data:
            conn = get_db()
            conn.execute("""
                INSERT OR IGNORE INTO achievement_counters (key, value)
                VALUES (?, 0)
            """, (f"species_tried_{data['species']}",))
            conn.execute("""
                UPDATE achievement_counters SET value=1
                WHERE key=?
            """, (f"species_tried_{data['species']}",))
            conn.commit()
            conn.close()

            all_species = ["cactus","peace_lily","monstera","succulent","fern","orchid","pothos"]
            tried = [get_counter(f"species_tried_{s}") for s in all_species]
            if all(t >= 1 for t in tried) and unlock("method_actor"):
                newly_unlocked.append("method_actor")

    return newly_unlocked


def get_achievement_details(achievement_id):
    return ACHIEVEMENTS.get(achievement_id)
