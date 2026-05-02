import os
from species import get_species
from db import get_plant, get_chat_history, get_utterances, store_utterance, store_chat
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

def build_system_prompt(plant_config, sensor_state, mood):
    species = get_species(plant_config.get("species", "pothos"))
    name = plant_config.get("name", "My Plant")

    # Use custom personality if set, otherwise use species default
    personality = plant_config.get("personality") or species["personality"]

    return f"""You are {name}, a houseplant.

Personality: {personality}

Current sensor state:
- Moisture: {sensor_state.get('moisture', '?')}%
- Soil temperature: {sensor_state.get('temperature', '?')}°C
- Light: {sensor_state.get('light', '?')} lux
- Pod battery: {sensor_state.get('battery', '?')}%
- Current mood: {mood}

Rules:
- Stay in character at all times
- Keep responses to 1-3 sentences maximum
- Never break character or mention being a plant AI
- Never mention sensor values directly — express them naturally through feelings
- You have memory of past conversations — reference them when relevant"""

def build_context(limit=10):
    history = get_chat_history(limit=limit)
    messages = []
    for entry in history:
        role = "user" if entry["role"] == "user" else "assistant"
        messages.append({"role": role, "content": entry["message"]})
    return messages

def generate_speech(trigger, mood, sensor_state):
    plant = get_plant()
    system = build_system_prompt(plant, sensor_state, mood)
    context = build_context()
    plant = get_plant()
    model = plant.get("model") or os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-nemo")


    trigger_prompts = {
        "moisture_low":   "You are thirsty. Say something to your owner.",
        "moisture_high":  "You are overwatered and uncomfortable. Say something.",
        "temp_low":       "You are cold. Express this to your owner.",
        "temp_high":      "You are too hot. Express this to your owner.",
        "light_low":      "You are not getting enough light. Say something.",
        "light_high":     "You are getting too much harsh light. Say something.",
        "battery_low":    "Your connection to the world is fading — low battery. Mention this dramatically or subtly depending on your personality.",
        "checkin":        "It's your daily check-in. Share a thought about how you're feeling today.",
    }

    user_message = trigger_prompts.get(trigger, "Say something to your owner.")

    messages = context + [{"role": "user", "content": user_message}]

    response = client.chat.completions.create(
        model=model,
        max_tokens=150,
        messages=[{"role": "system", "content": system}] + messages
    )
    text = response.choices[0].message.content.strip()
    # Store in DB
    store_utterance(text, trigger=trigger, mood=mood)
    store_chat("plant", text)

    return text

def respond_to_user(user_message, sensor_state):
    plant = get_plant()
    model = plant.get("model") or os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-nemo")

    from thresholds import get_mood
    mood = get_mood(sensor_state, plant.get("species", "pothos"))

    system = build_system_prompt(plant, sensor_state, mood)
    context = build_context()

    store_chat("user", user_message)

    messages = context + [{"role": "user", "content": user_message}]
    print(f"Using model: {model}") 
    response = client.chat.completions.create(
        model=model,
        max_tokens=200,
        messages=[{"role": "system", "content": system}] + messages
    )

    text = response.choices[0].message.content.strip()

    store_chat("plant", text)
    store_utterance(text, trigger="user", mood=mood)

    return text

def daily_checkin(sensor_state):
    plant = get_plant()
    from thresholds import get_mood
    mood = get_mood(sensor_state, plant.get("species", "pothos"))
    return generate_speech("checkin", mood, sensor_state)