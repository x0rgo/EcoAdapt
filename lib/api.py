from flask import Blueprint, request, jsonify, Response
from lib.db import (
    store_reading, get_latest, get_history,
    get_plant, save_plant, get_utterances,
    queue_command, get_pending_commands, ack_command,
    store_utterance, store_chat, get_chat_history
)
from lib.species import list_species
from lib.thresholds import check_reading, get_mood, get_recommendations
from lib.personality import generate_speech, respond_to_user
from lib.auth import login_required, get_current_user, api_key_or_login_required
import time
import uuid

api = Blueprint("api", __name__)

_last_bridge_seen = 0
_bridge_heartbeat_interval = 60

# In-memory registry for audio stream tokens (single-user hobby scale)
_stream_registry = {}

# Remote debug log — last 100 messages from pod (in-memory, resets on server restart)
_debug_log = []
_DEBUG_LOG_MAX = 100

def _cleanup_streams():
    now = time.time()
    expired = [sid for sid, cfg in _stream_registry.items() if now - cfg.get("created", 0) > 300]
    for sid in expired:
        _stream_registry.pop(sid, None)

# ─────────────────────────────────────────────────────────
# BRIDGE ENDPOINTS
# ─────────────────────────────────────────────────────────

@api.route("/api/reading", methods=["POST"])
@api_key_or_login_required
def receive_reading():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    user = request.api_user
    user_id = user["id"]

    moisture    = data.get("moisture", 0)
    temperature = data.get("temperature", 0)
    light       = data.get("light", 0)
    battery     = data.get("battery", 100)

    store_reading(moisture, temperature, light, battery, user_id)

    # Any successful reading means the bridge is online
    global _last_bridge_seen
    _last_bridge_seen = time.time()

    reading = {"moisture": moisture, "temperature": temperature,
               "light": light, "battery": battery}

    # Update tamagotchi
    from lib.tamagotchi import update_tamagotchi
    tama_state = update_tamagotchi(reading, user_id)

    # Check thresholds
    plant   = get_plant(user_id)
    species = plant.get("species", "pothos")
    triggers = check_reading(reading, species)

    speech = None
    if triggers:
        t    = triggers[0]
        mood = get_mood(reading, species)
        try:
            speech = generate_speech(t["type"], mood, reading, user_id)
        except Exception as e:
            print(f"Speech generation error: {e}")

    # Check achievements
    try:
        from lib.achievements import check_sensor_achievements
        history = get_history(hours=1, user_id=user_id)
        prev    = history[-2] if len(history) >= 2 else None
        new_ach = check_sensor_achievements(reading, prev, user_id)
        if new_ach:
            from lib.ws import socketio
            from lib.achievements import get_achievement_details
            for ach_id in new_ach:
                socketio.emit("achievement", get_achievement_details(ach_id))
    except Exception as e:
        print(f"Achievement check error: {e}")

    from lib.ws import emit_reading, emit_speech
    emit_reading(reading)
    if speech:
        emit_speech(speech, get_mood(reading, species), species)

    return jsonify({"ok": True, "speech": speech, "tamagotchi": tama_state}), 200


@api.route("/api/pod-debug", methods=["POST"])
@api_key_or_login_required
def receive_pod_debug():
    body = request.get_json()
    if not body:
        return jsonify({"error": "no data"}), 400

    entry = {
        "ts":     time.time(),
        "pod_id": body.get("pod_id", "unknown"),
        "data":   body.get("data", {}),
    }
    _debug_log.append(entry)
    if len(_debug_log) > _DEBUG_LOG_MAX:
        _debug_log.pop(0)

    from lib.ws import socketio
    socketio.emit("pod_debug", entry)
    return jsonify({"ok": True}), 200


@api.route("/api/pod-debug", methods=["GET"])
@login_required
def get_pod_debug():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(_debug_log[-limit:]), 200


@api.route("/api/pod-debug/enable", methods=["POST"])
@login_required
def toggle_pod_debug():
    user = get_current_user()
    body = request.get_json(silent=True) or {}
    enabled = bool(body.get("enabled", True))
    queue_command("SET_DEBUG", f'{{"value": {"true" if enabled else "false"}}}', user["id"])
    return jsonify({"ok": True, "debug": enabled}), 200


@api.route("/api/status", methods=["POST"])
def bridge_status():
    global _last_bridge_seen, _bridge_heartbeat_interval
    _last_bridge_seen = time.time()
    data = request.get_json() or {}
    if "interval" in data:
        _bridge_heartbeat_interval = int(data["interval"])
    from lib.ws import emit_status
    emit_status(True)
    return jsonify({"ok": True}), 200


@api.route("/api/bridge_online", methods=["GET"])
def bridge_online():
    if _last_bridge_seen == 0:
        return jsonify({"online": False}), 200
    grace  = _bridge_heartbeat_interval + 10
    online = (time.time() - _last_bridge_seen) < grace
    return jsonify({"online": online}), 200


@api.route("/api/commands/pending", methods=["GET"])
@api_key_or_login_required
def pending_commands():
    user     = request.api_user
    commands = get_pending_commands(user["id"])
    return jsonify(commands), 200


@api.route("/api/commands/<int:command_id>/ack", methods=["POST"])
@api_key_or_login_required
def ack(command_id):
    ack_command(command_id)
    return jsonify({"ok": True}), 200


# ─────────────────────────────────────────────────────────
# DASHBOARD ENDPOINTS
# ─────────────────────────────────────────────────────────

@api.route("/api/readings", methods=["GET"])
@login_required
def latest_reading():
    user    = get_current_user()
    reading = get_latest(user["id"])
    if not reading:
        reading = {
            "moisture": 55, "temperature": 21.0,
            "light": 3200, "battery": 100,
            "timestamp": "no data yet"
        }
    return jsonify(reading), 200


@api.route("/api/history", methods=["GET"])
@login_required
def history():
    user  = get_current_user()
    hours = request.args.get("hours", 24, type=int)
    data  = get_history(hours=hours, user_id=user["id"])
    return jsonify(data), 200


@api.route("/api/plant", methods=["GET"])
@login_required
def get_plant_config():
    user  = get_current_user()
    plant = get_plant(user["id"])
    return jsonify(plant), 200


@api.route("/api/plant", methods=["POST"])
@login_required
def update_plant_config():
    user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    save_plant(data, user["id"])

    from lib.achievements import check_interaction_achievements
    if "name" in data and data["name"]:
        check_interaction_achievements("name_given", user_id=user["id"])
    if "species" in data:
        check_interaction_achievements("species_changed",
                                       {"species": data["species"]},
                                       user_id=user["id"])

    if "mode" in data:
        queue_command("SET_MODE", f'{{"value": "{data["mode"]}"}}', user["id"])
    if "read_interval" in data:
        queue_command("SET_READ_INTERVAL",
                      f'{{"value": {data["read_interval"]}}}', user["id"])
    if "check_interval" in data:
        queue_command("SET_CHECK_INTERVAL",
                      f'{{"value": {data["check_interval"]}}}', user["id"])

    return jsonify({"ok": True}), 200


@api.route("/api/species", methods=["GET"])
def species_list():
    return jsonify(list_species()), 200


@api.route("/api/command", methods=["POST"])
@login_required
def send_command():
    user = get_current_user()
    data = request.get_json()
    if not data or "command" not in data:
        return jsonify({"error": "missing command"}), 400
    queue_command(data["command"], data.get("payload"), user["id"])
    return jsonify({"ok": True}), 200


@api.route("/api/chat", methods=["POST"])
@login_required
def chat():
    user = get_current_user()
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "missing message"}), 400

    reading = get_latest(user["id"]) or {
        "moisture": 55, "temperature": 21.0,
        "light": 3200, "battery": 100
    }

    try:
        response = respond_to_user(data["message"], reading, user["id"])
    except Exception as e:
        import traceback
        print("CHAT ERROR:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    try:
        from lib.achievements import check_interaction_achievements
        check_interaction_achievements("chat",
                                       {"message": data["message"]},
                                       user_id=user["id"])
    except Exception as e:
        print(f"Achievement check error: {e}")

    return jsonify({"response": response}), 200


@api.route("/api/utterances", methods=["GET"])
@login_required
def utterances():
    user  = get_current_user()
    limit = request.args.get("limit", 10, type=int)
    return jsonify(get_utterances(limit=limit, user_id=user["id"])), 200


@api.route("/api/recommendations", methods=["GET"])
@login_required
def recommendations():
    user    = get_current_user()
    reading = get_latest(user["id"]) or {
        "moisture": 55, "temperature": 21.0,
        "light": 3200, "battery": 100
    }
    plant = get_plant(user["id"])
    tips  = get_recommendations(reading, plant.get("species", "pothos"))
    return jsonify(tips), 200


@api.route("/api/checkin", methods=["POST"])
@login_required
def manual_checkin():
    import traceback
    user = get_current_user()
    try:
        reading = get_latest(user["id"]) or {
            "moisture": 55, "temperature": 21.0,
            "light": 3200, "battery": 100
        }
        plant  = get_plant(user["id"])
        mood   = get_mood(reading, plant.get("species", "pothos"))
        speech = generate_speech("checkin", mood, reading, user["id"])
        # Don't emit via WebSocket — response goes directly to caller
        return jsonify({"speech": speech}), 200
    except Exception as e:
        print("CHECKIN ERROR:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500                                                                                                                                      


@api.route("/api/tamagotchi", methods=["GET"])
@login_required
def tamagotchi_state():
    user = get_current_user()
    from lib.tamagotchi import get_state
    return jsonify(get_state(user["id"])), 200


@api.route("/api/achievements", methods=["GET"])
@login_required
def achievements():
    user = get_current_user()
    from lib.achievements import get_all_achievements
    return jsonify(get_all_achievements(user["id"])), 200


_GAME_ACHIEVEMENT_IDS = {
    "secret_garden", "click_100", "click_1000", "click_10000",
    "earn_1m", "earn_1b", "earn_1t",
    "buy_all", "mass_prod", "method",
    "pest_control", "exterminator", "apex",
}


@api.route("/api/achievements/unlock-game", methods=["POST"])
@login_required
def unlock_game_achievement():
    user = get_current_user()
    body = request.get_json(force=True, silent=True) or {}
    ach_id = (body.get("id") or "").strip()
    if ach_id not in _GAME_ACHIEVEMENT_IDS:
        return jsonify({"error": "invalid achievement id"}), 400
    from lib.achievements import unlock, get_achievement_details
    if unlock(ach_id, user["id"]):
        from lib.ws import socketio
        socketio.emit("achievement", get_achievement_details(ach_id))
    return jsonify({"ok": True}), 200


@api.route("/api/speak", methods=["POST"])
@login_required
def speak():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "missing text"}), 400

    from lib.tts import generate_audio
    user    = get_current_user()
    plant   = get_plant(user["id"])
    species = data.get("species", plant.get("species", "default"))
    model   = data.get("model", plant.get("tts_model"))
    speed   = data.get("speed", plant.get("speech_speed", 1.0))
    fmt     = data.get("format", plant.get("speech_format", "mp3"))

    audio_b64 = generate_audio(data["text"], species, model, speed, fmt)

    if audio_b64:
        return jsonify({"audio": audio_b64, "format": fmt}), 200
    else:
        return jsonify({"audio": None, "fallback": True}), 200


@api.route("/api/tts-models", methods=["GET"])
@login_required
def tts_models():
    from lib.tts import list_tts_models
    return jsonify(list_tts_models()), 200


@api.route("/api/speak/stream", methods=["POST"])
@login_required
def create_speak_stream():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "missing text"}), 400

    user  = get_current_user()
    plant = get_plant(user["id"])

    _cleanup_streams()

    stream_id = str(uuid.uuid4())
    _stream_registry[stream_id] = {
        "text": data["text"],
        "species": data.get("species", plant.get("species", "default")),
        "model": data.get("model", plant.get("tts_model")),
        "mood": data.get("mood", "neutral"),
        "speed": data.get("speed", plant.get("speech_speed", 1.0)),
        "format": data.get("format", plant.get("speech_format", "mp3")),
        "created": time.time()
    }

    return jsonify({"stream_url": f"/api/speak/stream/{stream_id}"}), 200


@api.route("/api/speak/stream/<stream_id>", methods=["GET"])
@login_required
def get_speak_stream(stream_id):
    config = _stream_registry.pop(stream_id, None)
    if not config:
        return jsonify({"error": "stream expired or invalid"}), 404

    from lib.tts import stream_audio
    model = config.get("model", "")
    is_gemini = "google" in (model or "").lower()

    def generate():
        buf = bytearray()
        try:
            for chunk in stream_audio(config["text"], config["species"], model,
                                       config.get("mood", "neutral"),
                                       config.get("speed", 1.0)):
                if chunk:
                    buf.extend(chunk)
            if is_gemini:
                import struct
                pcm = bytes(buf)
                sample_rate = 24000
                num_channels = 1
                bits = 16
                header = struct.pack('<4sI4s4sIHHIIHH4sI',
                    b'RIFF', 36 + len(pcm),
                    b'WAVE', b'fmt ', 16,
                    1, num_channels, sample_rate,
                    sample_rate * num_channels * bits // 8,
                    num_channels * bits // 8, bits,
                    b'data', len(pcm))
                yield header + pcm
            else:
                if buf:
                    yield bytes(buf)
        except Exception as e:
            print(f"Stream generation error: {e}")

    mimetype = "audio/wav" if is_gemini else "audio/mpeg"
    return Response(generate(), mimetype=mimetype)


# ─────────────────────────────────────────────────────────
# PUBLIC READ-ONLY VIEW
# ─────────────────────────────────────────────────────────

@api.route("/api/public/<username>", methods=["GET"])
def public_plant(username):
    from lib.auth import get_user_by_username
    user = get_user_by_username(username)
    if not user:
        return jsonify({"error": "user not found"}), 404

    reading = get_latest(user["id"]) or {
        "moisture": 55, "temperature": 21.0,
        "light": 3200, "battery": 100
    }
    plant      = get_plant(user["id"])
    utterances = get_utterances(limit=1, user_id=user["id"])

    from lib.tamagotchi import get_state
    tama = get_state(user["id"])

    return jsonify({
        "plant":      plant,
        "reading":    reading,
        "last_words": utterances[0] if utterances else None,
        "tamagotchi": tama,
    }), 200
