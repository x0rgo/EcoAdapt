"""
achievements.py — EcoAdapt achievement system — multi-user
"""

from datetime import datetime
from lib.db import get_db, get_plant, get_latest, get_history, get_chat_history, get_chat_history

ACHIEVEMENTS = {
    # ───────── Care ─────────
    "first_drink":      {"id":"first_drink","name":"First Drink","emoji":"💧","desc":"Moisture recovered from low for the first time.","category":"care","xp":10},
    "on_time":          {"id":"on_time","name":"On Time","emoji":"⏱️","desc":"Watered before hitting critical 5 times.","category":"care","xp":25},
    "week_streak":      {"id":"week_streak","name":"Week Streak","emoji":"🌿","desc":"7 days of healthy moisture levels.","category":"care","xp":50},
    "sun_seeker":       {"id":"sun_seeker","name":"Sun Seeker","emoji":"☀️","desc":"Good light levels maintained for 24 hours straight.","category":"care","xp":20},
    "overprotective":   {"id":"overprotective","name":"Overprotective","emoji":"🛡️","desc":"Checked on your plant 50+ times in a single day. Touch grass.","category":"care","xp":15},
    "plant_whisperer":  {"id":"plant_whisperer","name":"Plant Whisperer","emoji":"🤫","desc":"Sent 100 chat messages to your plant. It still doesn't understand you.","category":"care","xp":35},
    "goldilocks":       {"id":"goldilocks","name":"Goldilocks","emoji":"🥣","desc":"All three sensors in perfect range at the same time. Just right.","category":"care","xp":30},
    "tlc":              {"id":"tlc","name":"Tender Loving Care","emoji":"💖","desc":"Kept happiness above 90 for 72 hours straight.","category":"care","xp":60},

    # ───────── Interaction ─────────
    "first_words":      {"id":"first_words","name":"First Words","emoji":"💬","desc":"Sent your first chat message to the plant.","category":"interaction","xp":5},
    "chatterbox":       {"id":"chatterbox","name":"Chatterbox","emoji":"🗣️","desc":"Sent 50 chat messages.","category":"interaction","xp":30},
    "name_giver":       {"id":"name_giver","name":"Name Giver","emoji":"🏷️","desc":"Gave your plant a name.","category":"interaction","xp":10},
    "method_actor":     {"id":"method_actor","name":"Method Actor","emoji":"🎭","desc":"Tried all 7 plant species personalities.","category":"interaction","xp":40},
    "night_owl":        {"id":"night_owl","name":"Night Owl","emoji":"🌙","desc":"Chatted with your plant between 2am and 4am.","category":"interaction","xp":15},
    "philosopher":      {"id":"philosopher","name":"Philosopher","emoji":"🤖","desc":"Sent a message over 200 characters long.","category":"interaction","xp":10},
    "polyglot":         {"id":"polyglot","name":"Polyglot","emoji":"🌍","desc":"Changed plant species 5 times.","category":"interaction","xp":20},
    "confessional":     {"id":"confessional","name":"Confessional","emoji":"🙏","desc":"Wrote your plant a message over 1,000 characters. It's judging you.","category":"interaction","xp":25},
    "night_shift":      {"id":"night_shift","name":"Night Shift","emoji":"🦉","desc":"Chatted with your plant at night 5 times.","category":"interaction","xp":25},
    "drama_queen":      {"id":"drama_queen","name":"Drama Queen","emoji":"🎭","desc":"Triggered 10 dramatic peace lily speeches.","category":"interaction","xp":20},

    # ───────── Growth ─────────
    "sprouted":         {"id":"sprouted","name":"Sprouted","emoji":"🌱","desc":"Reached the Sprout life stage.","category":"growth","xp":0},
    "thriving_stage":   {"id":"thriving_stage","name":"Thriving","emoji":"🌳","desc":"Reached the maximum life stage.","category":"growth","xp":0},
    "century":          {"id":"century","name":"Century","emoji":"⭐","desc":"Accumulated 100 XP.","category":"growth","xp":0},
    "xp_hoarder":       {"id":"xp_hoarder","name":"XP Hoarder","emoji":"💰","desc":"Accumulated 500 XP. Absolute unit.","category":"growth","xp":0},
    "stage_five_clinger":{"id":"stage_five_clinger","name":"Stage Five Clinger","emoji":"🪤","desc":"Reached Thriving stage and stayed there 30 days. You're stuck with me.","category":"growth","xp":0},

    # ───────── Neglect ─────────
    "close_call":       {"id":"close_call","name":"Close Call","emoji":"😰","desc":"Plant hit critical moisture but recovered.","category":"neglect","xp":5},
    "comeback":         {"id":"comeback","name":"Comeback","emoji":"🏥","desc":"Happiness dropped below 20 then recovered above 80.","category":"neglect","xp":15},
    "ghost_owner":      {"id":"ghost_owner","name":"Ghost Owner","emoji":"👻","desc":"No readings for 3 days, then the plant recovered. It forgives you. I don't.","category":"neglect","xp":20},
    "neglect_king":     {"id":"neglect_king","name":"Neglect King","emoji":"👑","desc":"Happiness dropped below 10. How could you?","category":"neglect","xp":10},

    # ───────── Extreme ─────────
    "absolute_zero":    {"id":"absolute_zero","name":"Absolute Zero","emoji":"🥶","desc":"Uhm? Is your plant okay? Soil temperature dropped below 0°C.","category":"extreme","xp":20},
    "volcano":          {"id":"volcano","name":"Volcano","emoji":"🌋","desc":"Wow okay, you might be an arsonist... Soil temperature exceeded 45°C.","category":"extreme","xp":20},
    "surface_of_sun":   {"id":"surface_of_sun","name":"Surface of the Sun","emoji":"🔆","desc":"Light reading exceeded 50,000 lux.","category":"extreme","xp":25},
    "void":             {"id":"void","name":"The Void","emoji":"👁️","desc":"Recorded a 0 lux reading — complete darkness.","category":"extreme","xp":15},
    "brink":            {"id":"brink","name":"The Brink","emoji":"💀","desc":"Soil moisture hit 0%.","category":"extreme","xp":10},
    "atlantis":         {"id":"atlantis","name":"Atlantis","emoji":"🌊","desc":"Soil moisture hit 100%.","category":"extreme","xp":10},
    "flatliner":        {"id":"flatliner","name":"Flatliner","emoji":"🔋","desc":"Pod battery hit 0%.","category":"extreme","xp":10},
    "ghost_plant":      {"id":"ghost_plant","name":"Ghost Plant","emoji":"👻","desc":"No readings for 7 days, then one arrived.","category":"extreme","xp":15},
    "extremophile":     {"id":"extremophile","name":"Extremophile","emoji":"🧑‍🔬","desc":"Triggered all 4 extreme sensor achievements. You live in a hazard zone.","category":"extreme","xp":50},
    "time_traveler":    {"id":"time_traveler","name":"Time Traveler","emoji":"⏳","desc":"Moisture jumped over 50% between two readings. You're a wizard.","category":"extreme","xp":20},
    "sensor_nuke":      {"id":"sensor_nuke","name":"Sensor Nuke","emoji":"💥","desc":"Hit 3+ extreme conditions in a single reading. What have you done.","category":"extreme","xp":30},
    "zombie_plant":     {"id":"zombie_plant","name":"Zombie Plant","emoji":"🧟","desc":"Battery hit 0% and the plant still came back. It cannot be killed.","category":"extreme","xp":20},

    # ───────── Birthday ─────────
    "two_weeks":        {"id":"two_weeks","name":"Two Weeks","emoji":"🎂","desc":"Your plant has been alive for 15 days.","category":"birthday","xp":20},
    "one_month":        {"id":"one_month","name":"One Month","emoji":"🎉","desc":"Your plant has been alive for 30 days.","category":"birthday","xp":30},
    "sixty_days":       {"id":"sixty_days","name":"Two Months","emoji":"🌿","desc":"Your plant has been alive for 60 days.","category":"birthday","xp":40},
    "survivor":         {"id":"survivor","name":"Survivor","emoji":"💪","desc":"Your plant has been alive for 100 days.","category":"birthday","xp":50},
    "veteran":          {"id":"veteran","name":"Veteran","emoji":"🏆","desc":"Your plant has been alive for 180 days.","category":"birthday","xp":75},
    "elder":            {"id":"elder","name":"Elder","emoji":"🦯","desc":"Your plant has been alive for 500 days. It remembers the before-times.","category":"birthday","xp":150},
    "ancient":          {"id":"ancient","name":"Ancient","emoji":"🌳","desc":"Your plant has been alive for 365 days.","category":"birthday","xp":100},
    "legend":           {"id":"legend","name":"Legend","emoji":"👑","desc":"Your plant has been alive for 730 days.","category":"birthday","xp":200},
    "millennium":       {"id":"millennium","name":"Millennium","emoji":"🏛️","desc":"Your plant has been alive for 1,000 days. It predates your last hobby.","category":"birthday","xp":500},

    # ───────── Chaos ─────────
    "chaos_theory":     {"id":"chaos_theory","name":"Chaos Theory","emoji":"🦋","desc":"Switched plant species 10 times. Make up your mind!","category":"chaos","xp":30},
    "lightning_round":  {"id":"lightning_round","name":"Lightning Round","emoji":"⚡","desc":"Sent 5 chat messages within 60 seconds. Hyperfixation unlocked.","category":"chaos","xp":20},
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

    # Extremophile — all 4 sensor extremes triggered
    if (is_unlocked("absolute_zero", user_id) and is_unlocked("volcano", user_id)
            and is_unlocked("surface_of_sun", user_id) and is_unlocked("void", user_id)):
        u("extremophile")

    # Sensor nuke — 3+ extremes in one reading
    extreme_count = sum([temperature < 0, temperature > 45, light >= 50000, light == 0,
                         moisture <= 0, moisture >= 100, battery <= 0])
    if extreme_count >= 3:
        u("sensor_nuke")

    # Zombie plant — battery was 0 but now is > 0
    if prev_reading and prev_reading.get("battery", 100) <= 0 and battery > 0:
        u("zombie_plant")

    # Time traveler — moisture jump > 50 between readings
    if prev_reading and moisture - prev_reading.get("moisture", 50) > 50:
        u("time_traveler")

    # Watering
    if prev_reading:
        prev_m = prev_reading.get("moisture", 50)
        if moisture - prev_m > 15:
            u("first_drink")
            from lib.species import get_species
            config = get_species(plant.get("species", "pothos"))
            t = config["thresholds"]
            if prev_m > t["moisture_low"]:
                count = increment_counter("timely_waterings", user_id)
                if count >= 5: u("on_time")
            if prev_m < t["moisture_low"]:
                u("close_call")

    # Goldilocks — all sensors in perfect range right now
    from lib.species import get_species as _gs
    _cfg = _gs(plant.get("species", "pothos"))
    _th = _cfg["thresholds"]
    if (_th["moisture_low"] <= moisture <= _th["moisture_high"]
            and _th["temp_low"] <= temperature <= _th["temp_high"]
            and _th["light_low"] <= light <= _th["light_high"]):
        u("goldilocks")

    # Happiness comeback
    if happiness < 20:
        set_counter("min_happiness_seen", int(happiness), user_id)
    elif happiness > 80 and get_counter("min_happiness_seen", user_id) < 20:
        u("comeback")
        set_counter("min_happiness_seen", 100, user_id)

    # Overprotective — 50+ readings in the last 24 hours
    today_r = get_history(hours=24, user_id=user_id)
    if len(today_r) >= 50:
        u("overprotective")

    # TLC — happiness stays >= 90 across consecutive readings
    if happiness >= 90:
        tlc_cnt = increment_counter("tlc_readings", user_id)
        if tlc_cnt >= 72:
            u("tlc")
    else:
        set_counter("tlc_readings", 0, user_id)

    # Ghost owner — 3+ day gap between readings
    hist_3d = get_history(hours=72, user_id=user_id)
    if len(hist_3d) >= 2:
        lst  = datetime.fromisoformat(hist_3d[-1]["timestamp"])
        plst = datetime.fromisoformat(hist_3d[-2]["timestamp"])
        if (lst - plst).total_seconds() > 3 * 24 * 3600:
            u("ghost_owner")

    # Neglect king
    if happiness < 10:
        u("neglect_king")

    # XP + stage
    if xp >= 100:   u("century")
    if xp >= 500:   u("xp_hoarder")
    if stage >= 1:  u("sprouted")
    if stage >= 4:  u("thriving_stage")

    # Stage five clinger — thriving for 30 days
    if stage >= 4:
        import time as _time_mod
        s4_at = get_counter("stage4_reached_at", user_id)
        if s4_at == 0:
            set_counter("stage4_reached_at", int(_time_mod.time()), user_id)
        elif _time_mod.time() - s4_at >= 30 * 86400:
            u("stage_five_clinger")
    else:
        set_counter("stage4_reached_at", 0, user_id)

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
        from lib.species import get_species
        config = get_species(plant.get("species", "pothos"))
        t = config["thresholds"]
        if all(t["moisture_low"] <= r["moisture"] <= t["moisture_high"] for r in history_7d):
            u("week_streak")

    # Sun seeker
    history_24h = get_history(hours=24, user_id=user_id)
    if history_24h:
        from lib.species import get_species
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
        # Confessional — very long message (>=1000 chars)
        if data and len(data.get("message", "")) >= 1000:
            u("confessional")
        # Night shift — chat during late night (22-5) 5 times
        hour = datetime.now().hour
        if hour >= 22 or hour <= 5:
            night_cnt = increment_counter("night_chat", user_id)
            if night_cnt >= 5:
                u("night_shift")
        # Lightning round — 5 messages within 60 seconds
        now_ts = int(datetime.utcnow().timestamp())
        last_ts = get_counter("chat_last_ts", user_id)
        if last_ts and now_ts - last_ts <= 60:
            minute_cnt = increment_counter("chat_minute_cnt", user_id)
        else:
            set_counter("chat_minute_cnt", 1, user_id)
        set_counter("chat_last_ts", now_ts, user_id)
        if get_counter("chat_minute_cnt", user_id) >= 5:
            u("lightning_round")

    if interaction_type == "name_given":
        u("name_giver")

    if interaction_type == "species_changed":
        count = increment_counter("species_changes", user_id)
        if count >= 5: u("polyglot")
        if count >= 10: u("chaos_theory")
        if data and "species" in data:
            set_counter(f"species_tried_{data['species']}", 1, user_id)
            all_species = ["cactus","peace_lily","monstera","succulent","fern","orchid","pothos"]
            if all(get_counter(f"species_tried_{s}", user_id) >= 1 for s in all_species):
                u("method_actor")
            # Cactus fan — stay on cactus for 7 days
            if data["species"] == "cactus":
                cactus_start = get_counter("cactus_start_ts", user_id)
                now_ts = int(datetime.utcnow().timestamp())
                if cactus_start == 0:
                    set_counter("cactus_start_ts", now_ts, user_id)
                elif now_ts - cactus_start >= 7 * 86400:
                    u("cactus_fan")
            else:
                # Reset if switched away
                set_counter("cactus_start_ts", 0, user_id)
