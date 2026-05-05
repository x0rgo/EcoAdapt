import os, base64, requests

GPT_VOICES = {
    "cactus": "onyx", "peace_lily": "shimmer", "monstera": "verse",
    "succulent": "ash", "fern": "coral", "orchid": "nova",
    "pothos": "alloy", "default": "alloy",
}
GEMINI_VOICES = {
    "cactus": "Charon", "peace_lily": "Aoede", "monstera": "Kore",
    "succulent": "Fenrir", "fern": "Puck", "orchid": "Orus",
    "pothos": "Zephyr", "default": "Puck",
}
MOOD = {  # instructions for GPT, text prefix for Gemini
    "happy":       ("Speak with genuine warmth and enthusiasm. Bright, uplifted tone.", "[cheerful] "),
    "neutral":     ("Speak naturally and calmly.", ""),
    "thirsty":     ("Speak weak and desperate, like you desperately need water.", "[desperate] "),
    "overwatered": ("Speak with discomfort and nausea. Miserable.", "[miserable] "),
    "cold":        ("Speak shivering and trembling. Miserable and freezing.", "[shivering] "),
    "hot":         ("Speak panting and exhausted. Overheated.", "[exhausted] "),
    "dim":         ("Speak slowly and drowsily. Low energy.", "[drowsy] "),
    "bright":      ("Speak with vibrant energy and excitement.", "[energetic] "),
    "sad":         ("Speak softly and slowly. Melancholy and heavy.", "[sad] "),
    "angry":       ("Speak with sharp intensity and agitation.", "[angry] "),
    "scared":      ("Speak with a shaky, nervous voice. Anxious.", "[nervous] "),
    "screaming":    ("Speak LOUDLY with URGENCY. Full panic.", "[PANIC] "),
    "dead":        ("Speak in a flat, hollow whisper. Lifeless.", "[hollow] "),
}
API_URL = "https://openrouter.ai/api/v1/audio/speech"
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = "openai/gpt-4o-mini-tts-2025-12-15"

def _voice(species, model):
    prov = (model or "").split("/")[0]
    d = GEMINI_VOICES if prov == "google" else GPT_VOICES
    return d.get(species, d["default"])

def _payload(text, species, model, mood="neutral", speed=1.0, fmt="mp3"):
    voice = _voice(species, model)
    ml = (model or DEFAULT_MODEL).lower()
    p = {"model": model or DEFAULT_MODEL, "voice": voice, "response_format": "pcm" if "google" in ml else fmt or "mp3", "input": text}
    if "openai" in ml:
        p["speed"] = float(speed or 1.0)
    instr, prefix = MOOD.get(mood, MOOD["neutral"])
    if "gpt-4o" in ml or "mini-tts" in ml:
        p["instructions"] = instr
        p["input"] = text
    else:
        p["input"] = prefix + text
    return p

def generate_audio(text, species="default", model=None, mood="neutral", speed=1.0, fmt="mp3"):
    try:
        p = _payload(text, species, model, mood, speed, fmt)
        r = requests.post(API_URL, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, json=p, timeout=30)
        r.raise_for_status()
        return base64.b64encode(r.content).decode("utf-8")
    except Exception as e:
        print(f"TTS error: {e}")
        return None

def stream_audio(text, species="default", model=None, mood="neutral", speed=1.0, fmt="mp3"):
    try:
        p = _payload(text, species, model, mood, speed, fmt)
        r = requests.post(API_URL, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, json=p, stream=True, timeout=30)
        r.raise_for_status()
        for c in r.iter_content(4096):
            if c: yield c
    except Exception as e:
        print(f"TTS stream error: {e}")

def list_tts_models():
    return [
        {"id": "openai/gpt-4o-mini-tts-2025-12-15", "name": "GPT-4o Mini TTS"},
        {"id": "google/gemini-3.1-flash-tts-preview", "name": "Gemini 3.1 Flash TTS"},
    ]
