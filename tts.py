import os
import base64
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

# ← SPECIES_VOICES must come BEFORE generate_audio
SPECIES_VOICES = {
    "cactus":      {"model": "openai/gpt-4o-mini-tts-2025-12-15", "voice": "onyx",    "instructions": "Speak in a slow, dry, deadpan tone. Minimal emotion. Like a desert cowboy who has seen everything."},
    "peace_lily":  {"model": "openai/gpt-4o-mini-tts-2025-12-15", "voice": "shimmer", "instructions": "Speak dramatically and emotionally. Like a theatre actress performing a tragedy."},
    "monstera":    {"model": "openai/gpt-4o-mini-tts-2025-12-15", "voice": "verse",   "instructions": "Speak with confidence and warmth. Tropical energy. Like a charismatic host."},
    "succulent":   {"model": "openai/gpt-4o-mini-tts-2025-12-15", "voice": "ash",     "instructions": "Speak very calmly and quietly. Minimal words. Zen-like."},
    "fern":        {"model": "openai/gpt-4o-mini-tts-2025-12-15", "voice": "coral",   "instructions": "Speak with a slightly anxious, worried tone. Like someone constantly checking over their shoulder."},
    "orchid":      {"model": "openai/gpt-4o-mini-tts-2025-12-15", "voice": "nova",    "instructions": "Speak with sophistication and precision. Measured, elegant, slightly formal."},
    "pothos":      {"model": "openai/gpt-4o-mini-tts-2025-12-15", "voice": "alloy",   "instructions": "Speak cheerfully and warmly. Friendly and approachable. Like a golden retriever in voice form."},
    "default":     {"model": "openai/gpt-4o-mini-tts-2025-12-15", "voice": "alloy",   "instructions": "Speak naturally and warmly."},
}

def generate_audio(text, species="default"):
    config = SPECIES_VOICES.get(species, SPECIES_VOICES["default"])
    try:
        response = client.audio.speech.create(
            model=config["model"],
            voice=config["voice"],
            input=text,
            response_format="mp3",
            extra_body={"instructions": config["instructions"]}
        )
        audio_bytes = b""
        for chunk in response.iter_bytes():
            audio_bytes += chunk
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"TTS error: {e}")
        return None

def get_voice_config(species="default"):
    return SPECIES_VOICES.get(species, SPECIES_VOICES["default"])

def stream_audio(text, species="default"):
    config = SPECIES_VOICES.get(species, SPECIES_VOICES["default"])
    try:
        with client.audio.speech.with_streaming_response.create(
            model=config["model"],
            voice=config["voice"],
            input=text,
            response_format="mp3",
            extra_body={"instructions": config["instructions"]}
        ) as response:
            for chunk in response.iter_bytes(chunk_size=4096):
                yield chunk
    except Exception as e:
        print(f"TTS stream error: {e}")