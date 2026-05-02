from flask_socketio import SocketIO
from db import get_latest, get_utterances, get_plant

socketio = SocketIO(cors_allowed_origins="*")

def emit_reading(reading):
    socketio.emit("reading", reading)

def emit_speech(text, mood="neutral"):
    socketio.emit("speech", {"text": text, "mood": mood})

def emit_status(online: bool):
    socketio.emit("bridge_status", {"online": online})

def on_connect():
    # Send current state to newly connected client
    reading = get_latest()
    if reading:
        socketio.emit("reading", reading)

    utterances = get_utterances(limit=5)
    if utterances:
        latest = utterances[0]
        socketio.emit("speech", {
            "text": latest["text"],
            "mood": latest["mood"]
        })