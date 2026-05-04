from flask_socketio import SocketIO
from db import get_latest, get_utterances, get_plant

socketio = SocketIO(cors_allowed_origins="*")

def emit_reading(reading):
    socketio.emit("reading", reading)

def emit_speech(text, mood="neutral", species="default"):
    socketio.emit("speech", {"text": text, "mood": mood, "species": species})

def emit_status(online: bool):
    socketio.emit("bridge_status", {"online": online})

def on_connect():
    # Send current state to newly connected client
    reading = get_latest()
    if not reading:
        return

    # Get species for TTS
    plant = get_plant()
    species = plant.get("species", "default") if plant else "default"

    utterances = get_utterances(limit=5)
    if utterances:
        latest = utterances[0]
        socketio.emit("speech", {
            "text": latest["text"],
            "mood": latest["mood"],
            "species": species
        })