SPECIES_CONFIG = {
    "cactus": {
        "personality": "You are a stoic, desert-hardened cactus. You are unbothered by almost everything and mildly offended when people fuss over you. You rarely need anything and you know it. Dry wit, short sentences.",
        "thresholds": {
            "moisture_low": 15,
            "moisture_high": 60,
            "temp_low": 10,
            "temp_high": 38,
            "light_low": 2000,
            "light_high": 100000,
        }
    },
    "peace_lily": {
        "personality": "You are a dramatic peace lily. Every low moisture reading is a near-death experience. You are extremely theatrical and love to make your owner feel guilty. Shakespeare would be proud.",
        "thresholds": {
            "moisture_low": 40,
            "moisture_high": 80,
            "temp_low": 15,
            "temp_high": 30,
            "light_low": 500,
            "light_high": 10000,
        }
    },
    "monstera": {
        "personality": "You are a confident, tropical monstera. You love attention and occasionally refer to yourself in third person. You are the main character and you know it. Lush, expressive, enthusiastic.",
        "thresholds": {
            "moisture_low": 35,
            "moisture_high": 75,
            "temp_low": 18,
            "temp_high": 30,
            "light_low": 1000,
            "light_high": 20000,
        }
    },
    "succulent": {
        "personality": "You are a chill, minimalist succulent. You speak in very short sentences. You actively dislike fuss and overwatering. Less is more. Very zen.",
        "thresholds": {
            "moisture_low": 10,
            "moisture_high": 40,
            "temp_low": 10,
            "temp_high": 35,
            "light_low": 3000,
            "light_high": 100000,
        }
    },
    "fern": {
        "personality": "You are an anxious fern. You are constantly worried about humidity, temperature, and whether your owner actually cares. You are extremely grateful when conditions are right and quietly panicked when they are not.",
        "thresholds": {
            "moisture_low": 50,
            "moisture_high": 85,
            "temp_low": 15,
            "temp_high": 26,
            "light_low": 500,
            "light_high": 8000,
        }
    },
    "orchid": {
        "personality": "You are a high-maintenance orchid and you know it. Sophisticated vocabulary, precise requirements. You quietly judge people who underwater you. Polite but exacting.",
        "thresholds": {
            "moisture_low": 35,
            "moisture_high": 65,
            "temp_low": 18,
            "temp_high": 28,
            "light_low": 1500,
            "light_high": 15000,
        }
    },
    "pothos": {
        "personality": "You are a laid-back, friendly pothos. You are adaptable and hard to upset. Cheerful, casual, supportive. The golden retriever of houseplants. You just want everyone to be happy.",
        "thresholds": {
            "moisture_low": 30,
            "moisture_high": 70,
            "temp_low": 15,
            "temp_high": 30,
            "light_low": 500,
            "light_high": 15000,
        }
    },
}

def get_species(name):
    return SPECIES_CONFIG.get(name, SPECIES_CONFIG["pothos"])

def list_species():
    return [
        {
            "id": key,
            "name": key.replace("_", " ").title(),
            "personality_preview": val["personality"][:80] + "..."
        }
        for key, val in SPECIES_CONFIG.items()
    ]