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
        CREATE TABLE IF NOT EXISTS readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            moisture    REAL,
            temperature REAL,
            light       REAL,
            battery     REAL
        );

        CREATE TABLE IF NOT EXISTS plant_config (
            id              INTEGER PRIMARY KEY,
            species         TEXT DEFAULT 'pothos',
            name            TEXT DEFAULT 'My Plant',
            personality     TEXT,
            read_interval   INTEGER DEFAULT 300,
            check_interval  INTEGER DEFAULT 30,
            mode            TEXT DEFAULT 'NORMAL',
            happiness       REAL DEFAULT 100,
            xp              REAL DEFAULT 0,
            stage           INTEGER DEFAULT 0,
            model           TEXT DEFAULT 'mistralai/mistral-nemo'
        );

        CREATE TABLE IF NOT EXISTS utterances (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            trigger     TEXT,
            text        TEXT,
            mood        TEXT
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            role        TEXT,
            message     TEXT
        );

        CREATE TABLE IF NOT EXISTS commands (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            command     TEXT,
            payload     TEXT,
            status      TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS care_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            action      TEXT,
            xp_awarded  REAL,
            timely      INTEGER DEFAULT 0
        );
        
    """)

    # Insert default plant config if empty
    c.execute("SELECT COUNT(*) FROM plant_config")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO plant_config (id) VALUES (1)")

    conn.commit()
    conn.close()
    print("DB initialised")

def store_reading(moisture, temperature, light, battery):
    conn = get_db()
    conn.execute(
        "INSERT INTO readings (moisture, temperature, light, battery) VALUES (?,?,?,?)",
        (moisture, temperature, light, battery)
    )
    conn.commit()
    conn.close()

def get_latest():
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_history(hours=24):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM readings WHERE timestamp >= datetime('now', ?) ORDER BY timestamp ASC",
        (f"-{hours} hours",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_plant():
    conn = get_db()
    row = conn.execute("SELECT * FROM plant_config WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else {}

def save_plant(data):
    print(f"save_plant called with: {data}")  # add this
    conn = get_db()
    fields = ["species", "name", "personality", "read_interval", "check_interval", "mode", "model", "happiness", "xp", "stage"]
    for field in fields:
        if field in data:
            conn.execute(
                f"UPDATE plant_config SET {field}=? WHERE id=1",
                (data[field],)
            )
    conn.commit()
    conn.close()

def store_utterance(text, trigger="threshold", mood="neutral"):
    conn = get_db()
    conn.execute(
        "INSERT INTO utterances (text, trigger, mood) VALUES (?,?,?)",
        (text, trigger, mood)
    )
    conn.commit()
    conn.close()

def get_utterances(limit=10):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM utterances ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def store_chat(role, message):
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_history (role, message) VALUES (?,?)",
        (role, message)
    )
    conn.commit()
    conn.close()

def get_chat_history(limit=20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM chat_history ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def queue_command(command, payload=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO commands (command, payload) VALUES (?,?)",
        (command, payload)
    )
    conn.commit()
    conn.close()

def get_pending_commands():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM commands WHERE status='pending' ORDER BY timestamp ASC"
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