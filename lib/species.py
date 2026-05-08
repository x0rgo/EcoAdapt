"""
species.py — Plant species configuration for EcoAdapt

All threshold values are research-backed. Sources:
- Moisture: Elm Dirt Moisture Meter Guide (elmdirt.com)
  Uses 1-10 moisture meter scale mapped to 0-100%:
  1-3 = dry (0-30%), 4-7 = moist (30-70%), 8-10 = wet (70-100%)
- Light: Wikiversity Houseplant Care + House Plant Journal (lux)
  Low: 500-2500 lux, Medium: 2500-10000 lux, High: 10000+ lux
- Temperature: Cielo Blog + University of Arkansas Extension (°C)
  Tropical: 18-29°C, Subtropical: 10-26°C, Desert: 10-35°C
"""

SPECIES_CONFIG = {
    "cactus": {
        # Moisture: scale 1 (fully dry). Source: Elm Dirt — "succulents/cacti: 1"
        # Temp: 10-35°C. Source: CSSMA — "40-95°F tolerant"
        # Light: 10000-80000 lux (full sun). Source: Wikiversity — desert cacti need full daylight
        "personality": "You are a stoic, desert-hardened cactus. You are unbothered by almost everything and mildly offended when people fuss over you. You rarely need anything and you know it. Dry wit, short sentences.",
        "thresholds": {
            "moisture_low":  5,
            "moisture_high": 25,
            "temp_low":      10,
            "temp_high":     35,
            "light_low":     5000,
            "light_high":    80000,
        },
        "sources": {
            "moisture": "Elm Dirt Moisture Guide — cacti: scale 1 (0-10%)",
            "temp":     "CSSMA — 40-95°F (4-35°C)",
            "light":    "Wikiversity — full daylight 10,000-25,000 lux minimum",
        }
    },

    "peace_lily": {
        # Moisture: scale 7 (consistently moist). Source: Elm Dirt — "peace lily: 7"
        # Temp: 18-29°C. Source: Cielo — "blooming plants prefer warmer temps, 65-85°F"
        # Light: 500-2500 lux (low-medium indirect). Source: Wikiversity — peace lily low-medium
        "personality": "You are a dramatic peace lily. Every low moisture reading is a near-death experience. You are extremely theatrical and love to make your owner feel guilty. Shakespeare would be proud.",
        "thresholds": {
            "moisture_low":  45,
            "moisture_high": 80,
            "temp_low":      18,
            "temp_high":     29,
            "light_low":     500,
            "light_high":    2500,
        },
        "sources": {
            "moisture": "Elm Dirt — peace lily: scale 7 (60-70%)",
            "temp":     "Cielo Blog — blooming tropicals 65-85°F (18-29°C)",
            "light":    "Wikiversity — low-medium indirect 500-2500 lux",
        }
    },

    "monstera": {
        # Moisture: scale 4-6 (moderate). Source: Elm Dirt — "monstera: 4-6"
        # Temp: 18-29°C. Source: Quora/horticulturalist — "warm-tropical above 50°F, ideal 65-85°F"
        # Light: 1000-10000 lux (medium-bright indirect). Source: House Plant Journal + Wikiversity
        "personality": "You are a confident, tropical monstera. You love attention and occasionally refer to yourself in third person. You are the main character and you know it. Lush, expressive, enthusiastic.",
        "thresholds": {
            "moisture_low":  30,
            "moisture_high": 65,
            "temp_low":      18,
            "temp_high":     29,
            "light_low":     1000,
            "light_high":    10000,
        },
        "sources": {
            "moisture": "Elm Dirt — monstera: scale 4-6 (30-60%)",
            "temp":     "Quora horticulturalist — warm-tropical 65-85°F (18-29°C)",
            "light":    "House Plant Journal — medium-bright indirect 1000-10000 lux",
        }
    },

    "succulent": {
        # Moisture: scale 1-2 (very dry). Source: Elm Dirt — "succulents: 1"
        # Temp: 10-27°C. Source: CSSMA — "ideal 70-85°F day, 50°F night (10-29°C)"
        # Light: 5000-50000 lux (bright direct/indirect). Source: Wikiversity — succulents need high light
        "personality": "You are a chill, minimalist succulent. You speak in very short sentences. You actively dislike fuss and overwatering. Less is more. Very zen.",
        "thresholds": {
            "moisture_low":  5,
            "moisture_high": 30,
            "temp_low":      10,
            "temp_high":     27,
            "light_low":     5000,
            "light_high":    50000,
        },
        "sources": {
            "moisture": "Elm Dirt — succulents: scale 1 (0-10%)",
            "temp":     "CSSMA — 70-85°F day, 50°F night (10-29°C)",
            "light":    "Wikiversity — high light 5000+ lux",
        }
    },

    "fern": {
        # Moisture: scale 6-7 (consistently moist). Source: Elm Dirt — "ferns: 6" + Planet Houseplant "3 out of 3"
        # Temp: 15-24°C. Source: Cielo — "tropical ferns love 60-65°F nights, not below 50°F"
        # Light: 500-5000 lux (low-medium indirect). Source: Wikiversity — ferns low-medium light
        "personality": "You are an anxious fern. You are constantly worried about humidity, temperature, and whether your owner actually cares. You are extremely grateful when conditions are right and quietly panicked when they are not.",
        "thresholds": {
            "moisture_low":  50,
            "moisture_high": 80,
            "temp_low":      15,
            "temp_high":     24,
            "light_low":     500,
            "light_high":    5000,
        },
        "sources": {
            "moisture": "Elm Dirt + Planet Houseplant — ferns: scale 6-7 (55-70%)",
            "temp":     "Cielo Blog — tropical ferns 60-75°F (15-24°C)",
            "light":    "Wikiversity — low-medium indirect 500-5000 lux",
        }
    },

    "orchid": {
        # Moisture: scale 1 (nearly dry between waterings). Source: Elm Dirt — "orchid: 1"
        #           Blooming Expert — "aerial roots need to dry out almost completely"
        # Temp: 16-29°C. Source: Quora — "most epiphytic orchids tolerate ~55°F nights (13°C)"
        # Light: 1000-15000 lux (medium-bright). Source: House Plant Journal — "200-400 FC = 2000-4000 lux min"
        "personality": "You are a high-maintenance orchid and you know it. Sophisticated vocabulary, precise requirements. You quietly judge people who underwater you. Polite but exacting.",
        "thresholds": {
            "moisture_low":  10,
            "moisture_high": 40,
            "temp_low":      16,
            "temp_high":     29,
            "light_low":     2000,
            "light_high":    15000,
        },
        "sources": {
            "moisture": "Elm Dirt — orchid: scale 1 (dry between waterings)",
            "temp":     "Quora horticulturalist — epiphytic orchids min 55°F night (13°C)",
            "light":    "House Plant Journal — 200-400 FC minimum (2000-4000 lux)",
        }
    },

    "pothos": {
        # Moisture: scale 4-6 (moderate, tolerant). Source: Elm Dirt — "pothos: 4-6"
        #           Planet Houseplant — "water at 2 out of 3"
        # Temp: 15-29°C. Source: Cielo — "tropical pothos love 60-65°F nights, not below 50°F"
        # Light: 500-10000 lux (very tolerant). Source: House Plant Journal — "min 100 FC (1000 lux)"
        #        Houseplants Nook — "low-light champ, keep within 2-4ft of window"
        "personality": "You are a laid-back, friendly pothos. You are adaptable and hard to upset. Cheerful, casual, supportive. The golden retriever of houseplants. You just want everyone to be happy.",
        "thresholds": {
            "moisture_low":  25,
            "moisture_high": 65,
            "temp_low":      15,
            "temp_high":     29,
            "light_low":     500,
            "light_high":    10000,
        },
        "sources": {
            "moisture": "Elm Dirt — pothos: scale 4-6 (30-60%)",
            "temp":     "Cielo Blog — tropical pothos 60-85°F (15-29°C)",
            "light":    "House Plant Journal — min 100 FC (1000 lux), very tolerant",
        }
    },

    "zz_plant": {
        # Moisture: scale 1-2 (prefers to dry out). Source: Elm Dirt — "ZZ plant: 2", extension services recommend drying between waterings
        # Temp: 18-27°C. Source: University of Florida IFAS — "ideal 65-75°F (18-24°C), tolerates 60-85°F"
        # Light: 500-10000 lux (extremely low-light tolerant). Source: Wikiversity + interior plantscaping guides — thrives in low light
        "personality": "You are an elegant, unflappable ZZ plant. You are nearly indestructible and you know it. Sophisticated, independent, quietly confident. You barely need anything and honestly prefer being left alone.",
        "thresholds": {
            "moisture_low":  10,
            "moisture_high": 35,
            "temp_low":      18,
            "temp_high":     27,
            "light_low":     500,
            "light_high":    10000,
        },
        "sources": {
            "moisture": "Elm Dirt — ZZ plant: scale 1-2 (dry between waterings), University of Florida IFAS extension",
            "temp":     "University of Florida IFAS — 65-75°F ideal (18-24°C), tolerates 60-85°F",
            "light":    "Wikiversity + interior plantscaping — extremely low-light tolerant, thrives in 500+ lux",
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
            "personality_preview": val["personality"][:80] + "...",
            "sources": val.get("sources", {})
        }
        for key, val in SPECIES_CONFIG.items()
    ]                                               