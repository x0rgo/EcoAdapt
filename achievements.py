"""
achievements.py — EcoAdapt achievement system — multi-user
"""

from datetime import datetime
from db import get_db, get_plant, get_latest, get_history, get_chat_history

ACHIEVEMENTS = {
    "first_drink":    {"id":"first_drink","name":"First Drink","emoji":"💧","desc":"Moisture recovered from low for the first time.","category":"care","xp":10},
    "on_time":        {"id":"on_time","name":"On Time","emoji":"⏱️","desc":"Watered before hitting critical 5 times.","category":"care","xp":25},
    "week_streak":    {"id":"week_streak","name":"Week Streak","emoji":"🌿","desc":"7 days of healthy moisture levels.","category":"care","xp":50},
    "sun_seeker":     {"id":"sun_seeker","name":"Sun Seeker","emoji":"☀️","desc":"Good light levels maintained for 24 hours straight.","category":"care","xp":20},
    "first_words":    {"id":"first_words","name":"First Words","emoji":"💬","desc":"Sent your first chat message to the plant.","category":"interaction","xp":5},
    "chatterbox":     {"id":"chatterbox","name":"Chatterbox","emoji":"🗣️","desc":"Sent 50 chat messages.","category":"interaction","xp":30},
    "name_giver":     {"id":"name_giver","name":"Name Giver","emoji":"🏷️","desc":"Gave your plant a name.","category":"interaction","xp":10},
    "method_actor":   {"id":"method_actor","name":"Method Actor","emoji":"🎭","desc":"Tried all 7 plant species personalities.","category":"interaction","xp":40},
    "night_owl":      {"id":"night_owl","name":"Night Owl","emoji":"🌙","desc":"Chatted with your plant between 2am and 4am.","category":"interaction","xp":15},
    "philosopher":    {"id":"philosopher","name":"Philosopher","emoji":"🤖","desc":"Sent a message over 200 characters long.","category":"interaction","xp":10},
    "polyglot":       {"id":"polyglot","name":"Polyglot","emoji":"🌍","desc":"Changed plant species 5 times.","category":"interaction","xp":20},
    "sprouted":       {"id":"sprouted","name":"Sprouted","emoji":"🌱","desc":"Reached the Sprout life stage.","category":"growth","xp":0},
    "thriving_stage": {"id":"thriving_stage","name":"Thriving","emoji":"🌳","desc":"Reached the maximum life stage.","category":"growth","xp":0},
    "century":        {"id":"century","name":"Century","emoji":"⭐","desc":"Accumulated 100 XP.","category":"growth","xp":0},
    "close_call":     {"id":"close_call","name":"Close Call","emoji":"😰","desc":"Plant hit critical moisture but recovered.","category":"neglect","xp":5},
    "comeback":       {"id":"comeback","name":"Comeback","emoji":"🏥","desc":"Happiness dropped below 20 then recovered above 80.","category":"neglect","xp":15},
    "absolute_zero":  {"id":"absolute_zero","name":"Absolute Zero","emoji":"🥶","desc":"Uhm? Is your plant okay? Soil temperature dropped below 0°C.","category":"extreme","xp":20},
    "volcano":        {"id":"volcano","name":"Volcano","emoji":"🌋","desc":"Wow okay, you might be an arsonist... Soil temperature exceeded 45°C.","category":"extreme","xp":20},
    "surface_of_sun": {"id":"surface_of_sun","name":"Surface of the Sun","emoji":"🔆","desc":"Light reading exceeded 50,000 lux.","category":"extreme","xp":25},
    "void":           {"id":"void","name":"The Void","emoji":"👁️","desc":"Recorded a 0 lux reading — complete darkness.","category":"extreme","xp":15},
    "brink":          {"id":"brink","name":"The Brink","emoji":"💀","desc":"Soil moisture hit 0%.","category":"extreme","xp":10},
    "atlantis":       {"id":"atlantis","name":"Atlantis","emoji":"🌊","desc":"Soil moisture hit 100%.","category":"extreme","xp":10},
    "flatliner":      {"id":"flatliner","name":"Flatliner","emoji":"🔋","desc":"Pod battery hit 0%.","category":"extreme","xp":10},
    "ghost_plant":    {"id":"ghost_plant","name":"Ghost Plant","emoji":"👻","desc":"No readings for 7 days, then one arrived.","category":"extreme","xp":15},
    "two_weeks":      {"id":"two_weeks","name":"Two Weeks","emoji":"🎂","desc":"Your plant has been alive for 15 days.","category":"birthday","xp":20},
    "one_month":      {"id":"one_month","name":"One Month","emoji":"🎉","desc":"Your plant has been alive for 30 days.","category":"birthday","xp":30},
    "sixty_days":     {"id":"sixty_days","name":"Thriving","emoji":"🌿","desc":"Your plant has been alive for 60 days.","category":"birthday","xp":40},
    "survivor":       {"id":"survivor","name":"Survivor","emoji":"💪","desc":"Your plant has been alive for 100 days.","category":"birthday","xp":50},
    "veteran":        {"id":"veteran","name":"Veteran","emoji":"🏆","desc":"Your plant has been alive for 180 days.","category":"birthday","xp":75},
    "ancient":        {"id":"ancient","name":"Ancient","emoji":"🌳","desc":"Your plant has been alive for 365 days.","category":"birthday","xp":100},
    "legend":         {"id":"legend","name":"Legend","emoji":"👑","desc":"Your plant has been alive for 730 days.","category":"birthday","xp":200},
}

# ─────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────

def init_achievements_db():
    # Tables already created in db.py init_db — nothing to do here
    pass

def is_unlocked(achievement_id, user_id=1):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM achievements WHERE id=? AND user_id=?",
        (achievement_id, user_id)
    ).fetchone()
    conn.close()
    return row is not None

def unlock(achievement_id, user_id=1):
    if is_unlocked(achievement_id, user_id):
        return False
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO achievements (id, user_id) VALUES (?,?)",
        (achievement_id, user_id)
    )
    conn.commit()
    conn.close()
    return True

def get_counter(key, user_id=1):
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM achievement_counters WHERE key=? AND user_id=?",
        (key, user_id)
    ).fetchone()
    conn.close()
    return row["value"] if row else 0

def increment_counter(key, user_id=1, amount=1):
    conn = get_db()
    conn.execute("""
        INSERT INTO achievement_counters (key, user_id, value) VALUES (?,?,?)
        ON CONFLICT(key, user_id) DO UPDATE SET value = value + ?
    """, (key, user_id, amount, amount))
    conn.commit()
    conn.close()
    return get_counter(key, user_id)

def set_counter(key, value, user_id=1):
    conn = get_db()
    conn.execute("""
        INSERT INTO achievement_counters (key, user_id, value) VALUES (?,?,?)
        ON CONFLICT(key, user_id) DO UPDATE SET value = ?
    """, (key, user_id, value, value))
    conn.commit()
    conn.close()

def get_all_achievements(user_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, unlocked_at FROM achievements WHERE user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()
    unlocked = {r["id"]: r["unlocked_at"] for r in rows}
    result = []
    for ach_id, ach in ACHIEVEMENTS.items():
        result.append({
            **ach,
            "unlocked":    ach_id in unlocked,
            "unlocked_at": unlocked.get(ach_id)
        })
    return result

def get_achievement_details(achievement_id):
    return ACHIEVEMENTS.get(achievement_id)

def get_first_reading_date(user_id=1):
    conn = get_db()
    row = conn.execute(
        "SELECT timestamp FROM readings WHERE user_id=? ORDER BY timestamp ASC LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return datetime.fromisoformat(row["timestamp"])
    return None

# ─────────────────────────────────────────────────────────
# SENSOR ACHIEVEMENTS
# ─────────────────────────────────────────────────────────

def check_sensor_achievements(reading, prev_reading=None, user_id=1):
    newly_unlocked = []

    moisture    = reading.get("moisture", 50)
    temperature = reading.get("temperature", 20)
    light       = reading.get("light", 1000)
    battery     = reading.get("battery", 100)

    plant     = get_plant(user_id)
    happiness = float(plant.get("happiness", 100))
    xp        = float(plant.get("xp", 0))
    stage     = int(plant.get("stage", 0))

    def u(ach_id):
        if unlock(ach_id, user_id):
            newly_unlocked.append(ach_id)

    # Extreme
    if temperature < 0:   u("absolute_zero")
    if temperature > 45:  u("volcano")
    if light >= 50000:    u("surface_of_sun")
    if light == 0:        u("void")
    if moisture <= 0:     u("brink")
    if moisture >= 100:   u("atlantis")
    if battery <= 0:      u("flatliner")

    # Watering
    if prev_reading:
        prev_m = prev_reading.get("moisture", 50)
        if moisture - prev_m > 15:
            u("first_drink")
            from species import get_species
            config = get_species(plant.get("species", "pothos"))
            t = config["thresholds"]
            if prev_m > t["moisture_low"]:
                count = increment_counter("timely_waterings", user_id)
                if count >= 5: u("on_time")
            if prev_m < t["moisture_low"]:
                u("close_call")

    # Happiness comeback
    if happiness < 20:
        set_counter("min_happiness_seen", int(happiness), user_id)
    elif happiness > 80 and get_counter("min_happiness_seen", user_id) < 20:
        u("comeback")
        set_counter("min_happiness_seen", 100, user_id)

    # XP + stage
    if xp >= 100:  u("century")
    if stage >= 1: u("sprouted")
    if stage >= 4: u("thriving_stage")

    # Ghost plant
    history = get_history(hours=168, user_id=user_id)
    if len(history) >= 2:
        last        = datetime.fromisoformat(history[-1]["timestamp"])
        second_last = datetime.fromisoformat(history[-2]["timestamp"])
        if (last - second_last).total_seconds() > 7 * 24 * 3600:
            u("ghost_plant")

    # Birthday milestones
    first = get_first_reading_date(user_id)
    if first:
        days_alive = (datetime.utcnow() - first).days
        for days, ach_id in [(15,"two_weeks"),(30,"one_month"),(60,"sixty_days"),
                              (100,"survivor"),(180,"veteran"),(365,"ancient"),(730,"legend")]:
            if days_alive >= days: u(ach_id)

    # Week streak
    history_7d = get_history(hours=168, user_id=user_id)
    if len(history_7d) >= 288:
        from species import get_species
        config = get_species(plant.get("species", "pothos"))
        t = config["thresholds"]
        if all(t["moisture_low"] <= r["moisture"] <= t["moisture_high"] for r in history_7d):
            u("week_streak")

    # Sun seeker
    history_24h = get_history(hours=24, user_id=user_id)
    if history_24h:
        from species import get_species
        config = get_species(plant.get("species", "pothos"))
        t = config["thresholds"]
        daytime = [r for r in history_24h
                   if 7 <= datetime.fromisoformat(r["timestamp"]).hour <= 21]
        if daytime and all(r["light"] >= t["light_low"] for r in daytime):
            u("sun_seeker")

    return newly_unlocked

# ─────────────────────────────────────────────────────────
# INTERACTION ACHIEVEMENTS
# ─────────────────────────────────────────────────────────

def check_interaction_achievements(interaction_type, data=None, user_id=1):
    newly_unlocked = []

    def u(ach_id):
        if unlock(ach_id, user_id):
            newly_unlocked.append(ach_id)

    if interaction_type == "chat":
        count = increment_counter("chat_messages", user_id)
        if count == 1:  u("first_words")
        if count >= 50: u("chatterbox")
        if 2 <= datetime.now().hour < 4: u("night_owl")
        if data and len(data.get("message", "")) > 200: u("philosopher")

    if interaction_type == "name_given":
        u("name_giver")

    if interaction_type == "species_changed":
        count = increment_counter("species_changes", user_id)
        if count >= 5: u("polyglot")
        if data and "species" in data:
            set_counter(f"species_tried_{data['species']}", 1, user_id)
            all_species = ["cactus","peace_lily","monstera","succulent","fern","orchid","pothos"]
            if all(get_counter(f"species_tried_{s}", user_id) >= 1 for s in all_species):
                u("method_actor")

    return newly_unlocked