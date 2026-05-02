from flask import Blueprint, request, jsonify
from db import (
    store_reading, get_latest, get_history,
    get_plant, save_plant, get_utterances,
    queue_command, get_pending_commands, ack_command,
    store_utterance
)
from species import list_species
from thresholds import check_reading, get_mood, get_recommendations
from personality import generate_speech, respond_to_user
import time

_last_bridge_seen = 0
_bridge_heartbeat_interval = 60  # default assumption

api = Blueprint("api", __name__)

# ─────────────────────────────────────────
# BRIDGE ENDPOINTS
# ─────────────────────────────────────────

@api.route("/api/reading", methods=["POST"])
@api.route("/api/reading", methods=["POST"])
def receive_reading():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    moisture    = data.get("moisture", 0)
    temperature = data.get("temperature", 0)
    light       = data.get("light", 0)
    battery     = data.get("battery", 100)

    # Store in DB
    store_reading(moisture, temperature, light, battery)

    # Update tamagotchi state ← ADD THIS
    from tamagotchi import update_tamagotchi
    reading = {"moisture": moisture, "temperature": temperature,
               "light": light, "battery": battery}
    tama_state = update_tamagotchi(reading)

    # Check thresholds
    plant = get_plant()
    species = plant.get("species", "pothos")
    triggers = check_reading(reading, species)

    speech = None
    if triggers:
        t = triggers[0]
        mood = get_mood(reading, species)
        try:
            speech = generate_speech(t["type"], mood, reading)
        except Exception as e:
            print(f"Speech generation error: {e}")

    # Emit via WebSocket
    from ws import emit_reading, emit_speech
    emit_reading(reading)
    socketio.emit("tamagotchi", tama_state)
    if speech:
        emit_speech(speech, get_mood(reading, species))

    return jsonify({"ok": True, "speech": speech, "tamagotchi": tama_state}), 200

@api.route("/api/tamagotchi", methods=["GET"])
def tamagotchi_state():
    from tamagotchi import get_state
    return jsonify(get_state()), 200

@api.route("/api/status", methods=["POST"])
def bridge_status():
    global _last_bridge_seen, _bridge_heartbeat_interval
    _last_bridge_seen = time.time()
    data = request.get_json() or {}
    if "interval" in data:
        _bridge_heartbeat_interval = int(data["interval"])
    from ws import emit_status
    emit_status(True)
    return jsonify({"ok": True}), 200

@api.route("/api/commands/pending", methods=["GET"])
def pending_commands():
    commands = get_pending_commands()
    return jsonify(commands), 200


@api.route("/api/commands/<int:command_id>/ack", methods=["POST"])
def ack(command_id):
    ack_command(command_id)
    return jsonify({"ok": True}), 200

@api.route("/api/bridge_online", methods=["GET"])
def bridge_online():
    if _last_bridge_seen == 0:
        return jsonify({"online": False}), 200
    grace = _bridge_heartbeat_interval + 10
    online = (time.time() - _last_bridge_seen) < grace
    return jsonify({"online": online}), 200
# ─────────────────────────────────────────
# DASHBOARD ENDPOINTS
# ─────────────────────────────────────────

@api.route("/api/readings", methods=["GET"])
def latest_reading():
    reading = get_latest()
    if not reading:
        # Return mock data if no real readings yet
        reading = {
            "moisture": 55,
            "temperature": 21.0,
            "light": 3200,
            "battery": 100,
            "timestamp": "no data yet"
        }
    return jsonify(reading), 200


@api.route("/api/history", methods=["GET"])
def history():
    hours = request.args.get("hours", 24, type=int)
    data = get_history(hours=hours)
    return jsonify(data), 200


@api.route("/api/plant", methods=["GET"])
def get_plant_config():
    plant = get_plant()
    return jsonify(plant), 200


@api.route("/api/plant", methods=["POST"])
def update_plant_config():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400
    save_plant(data)

    # If mode changed, queue command to pod
    if "mode" in data:
        queue_command("SET_MODE", f'{{"mode": "{data["mode"]}"}}'  )
    if "read_interval" in data:
        queue_command("SET_READ_INTERVAL", f'{{"value": {data["read_interval"]}}}')
    if "check_interval" in data:
        queue_command("SET_CHECK_INTERVAL", f'{{"value": {data["check_interval"]}}}')

    return jsonify({"ok": True}), 200


@api.route("/api/species", methods=["GET"])
def species_list():
    return jsonify(list_species()), 200


@api.route("/api/command", methods=["POST"])
def send_command():
    data = request.get_json()
    if not data or "command" not in data:
        return jsonify({"error": "missing command"}), 400
    queue_command(data["command"], data.get("payload"))
    return jsonify({"ok": True}), 200


@api.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "missing message"}), 400

    reading = get_latest() or {
        "moisture": 55, "temperature": 21.0,
        "light": 3200, "battery": 100
    }

    try:
        response = respond_to_user(data["message"], reading)
    except Exception as e:
        import traceback
        print("CHAT ERROR:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    

    return jsonify({"response": response}), 200


@api.route("/api/utterances", methods=["GET"])
def utterances():
    limit = request.args.get("limit", 10, type=int)
    return jsonify(get_utterances(limit=limit)), 200


@api.route("/api/recommendations", methods=["GET"])
def recommendations():
    reading = get_latest() or {
        "moisture": 55, "temperature": 21.0,
        "light": 3200, "battery": 100
    }
    plant = get_plant()
    tips = get_recommendations(reading, plant.get("species", "pothos"))
    return jsonify(tips), 200


@api.route("/api/checkin", methods=["POST"])
def manual_checkin():
    reading = get_latest() or {
        "moisture": 55, "temperature": 21.0,
        "light": 3200, "battery": 100
    }
    plant = get_plant()
    from thresholds import get_mood
    mood = get_mood(reading, plant.get("species", "pothos"))
    try:
        speech = generate_speech("checkin", mood, reading)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    from ws import emit_speech
    emit_speech(speech, mood)

    return jsonify({"speech": speech}), 200