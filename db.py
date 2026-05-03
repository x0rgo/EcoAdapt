import sqlite3
from datetime import datetime
import os

DB_PATH = os.environ.get("DB_PATH", "ecoadapt.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            api_key     TEXT UNIQUE NOT NULL,
            difficulty  TEXT DEFAULT 'NORMAL',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            moisture    REAL,
            temperature REAL,
            light       REAL,
            battery     REAL,
            user_id     INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS plant_config (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER UNIQUE,
            species         TEXT DEFAULT 'pothos',
            name            TEXT DEFAULT 'My Plant',
            personality     TEXT,
            read_interval   INTEGER DEFAULT 300,
            check_interval  INTEGER DEFAULT 30,
            mode            TEXT DEFAULT 'NORMAL',
            model           TEXT DEFAULT 'mistralai/mistral-nemo',
            happiness       REAL DEFAULT 100,
            xp              REAL DEFAULT 0,
            stage           INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS utterances (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            trigger     TEXT,
            text        TEXT,
            mood        TEXT,
            user_id     INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            role        TEXT,
            message     TEXT,
            user_id     INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS commands (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            command     TEXT,
            payload     TEXT,
            status      TEXT DEFAULT 'pending',
            user_id     INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS care_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            action      TEXT,
            xp_awarded  REAL,
            timely      INTEGER DEFAULT 0,
            user_id     INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS achievements (
            id          TEXT,
            user_id     INTEGER DEFAULT 1,
            unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, user_id)
        );

        CREATE TABLE IF NOT EXISTS achievement_counters (
            key     TEXT,
            user_id INTEGER DEFAULT 1,
            value   INTEGER DEFAULT 0,
            PRIMARY KEY (key, user_id)
        );
    """)

    conn.commit()
    conn.close()
    print("DB initialised")

    try:
        from auth import init_users_db
        init_users_db()
    except Exception as e:
        print(f"Auth DB init error: {e}")

    try:
        from achievements import init_achievements_db
        init_achievements_db()
    except Exception as e:
        print(f"Achievements DB init error: {e}")

# ─────────────────────────────────────────────────────────
# READINGS
# ─────────────────────────────────────────────────────────

def store_reading(moisture, temperature, light, battery, user_id=1):
    conn = get_db()
    conn.execute(
        "INSERT INTO readings (moisture, temperature, light, battery, user_id) VALUES (?,?,?,?,?)",
        (moisture, temperature, light, battery, user_id)
    )
    conn.commit()
    conn.close()

def get_latest(user_id=1):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM readings WHERE user_id=? ORDER BY timestamp DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_history(hours=24, user_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM readings WHERE user_id=? AND timestamp >= datetime('now', ?) ORDER BY timestamp ASC",
        (user_id, f"-{hours} hours")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────────────────
# PLANT CONFIG
# ─────────────────────────────────────────────────────────

def get_plant(user_id=1):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM plant_config WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}

def save_plant(data, user_id=1):
    conn = get_db()
    fields = ["species", "name", "personality", "read_interval",
              "check_interval", "mode", "model", "happiness", "xp", "stage"]
    for field in fields:
        if field in data:
            conn.execute(
                f"UPDATE plant_config SET {field}=? WHERE user_id=?",
                (data[field], user_id)
            )
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────────────────
# UTTERANCES
# ─────────────────────────────────────────────────────────

def store_utterance(text, trigger="threshold", mood="neutral", user_id=1):
    conn = get_db()
    conn.execute(
        "INSERT INTO utterances (text, trigger, mood, user_id) VALUES (?,?,?,?)",
        (text, trigger, mood, user_id)
    )
    conn.commit()
    conn.close()

def get_utterances(limit=10, user_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM utterances WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────────────────
# CHAT HISTORY
# ─────────────────────────────────────────────────────────

def store_chat(role, message, user_id=1):
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_history (role, message, user_id) VALUES (?,?,?)",
        (role, message, user_id)
    )
    conn.commit()
    conn.close()

def get_chat_history(limit=20, user_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM chat_history WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

# ─────────────────────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────────────────────

def queue_command(command, payload=None, user_id=1):
    conn = get_db()
    conn.execute(
        "INSERT INTO commands (command, payload, user_id) VALUES (?,?,?)",
        (command, payload, user_id)
    )
    conn.commit()
    conn.close()

def get_pending_commands(user_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM commands WHERE status='pending' AND user_id=? ORDER BY timestamp ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def ack_command(command_id):
    conn = get_db()
    conn.execute(
        "UPDATE commands SET status='acked' WHERE id=?", (command_id,)
    )
    conn.commit()
    conn.close()