import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger("eyes_up.llm")

# Curated fallback knowledge base for when Ollama is offline or unavailable
CURATED_FIELD_TIPS: Dict[str, str] = {
    "american robin": "Look for a warm brick-red breast on open lawns and listen for a cheerful, lilting 'cheerily, cheer up' carol.",
    "northern cardinal": "Look for bright crimson plumage with a black face mask and crested head; listen for loud, metallic whistling calls.",
    "blue jay": "Look for vivid blue and white plumage with a prominent crest; listen for loud, raspy 'jay-jay' alarm calls in woodland edges.",
    "black-capped chickadee": "Look for a black cap and bib with white cheeks; listen for their crisp, namesake 'chick-a-dee-dee-dee' call.",
    "mourning dove": "Look for a slender, grayish-brown body with black spots on the wings; listen for a gentle, mournful 'coo-OO-oo' song.",
    "song sparrow": "Look for brown streaking converging into a central chest spot; listen for three brisk notes followed by a lively trill.",
    "red-winged blackbird": "Look for glossy black feathers with bright red and yellow shoulder epaulets; listen for a harsh 'conk-la-ree' call near wetlands.",
    "european starling": "Look for glossy, iridescent dark plumage speckled with white stars; listen for varied squeaks, whistles, and mimicry.",
    "house sparrow": "Look for a gray crown, black bib, and chestnut back on males; listen for repeated simple chirp notes around buildings.",
    "mallard": "Look for the male's iridescent green head and white neck ring; listen for classic female quacks and quiet male rasps near ponds.",
    "house finch": "Look for rosy red on the forehead and breast of males with brownish streaked flanks; listen for a bright, warbling song.",
    "white-breasted nuthatch": "Look for a blue-gray back and white face crawling head-first down tree trunks; listen for nasal 'yank-yank' calls.",
    "tufted titmouse": "Look for an all-gray body with a jaunty head crest and peachy flanks; listen for clear, repeated 'peter-peter-peter' whistles.",
    "downy woodpecker": "Look for a checkered black-and-white pattern with a white back patch; listen for a gentle whinny or sharp 'pik' tap.",
    "crow": "Look for an entirely black plumage and heavy bill; listen for the familiar harsh 'caw-caw' in varied open habitats.",
    "american goldfinch": "Look for bright yellow body and black wings with white wingbars in summer; listen for bouncing 'po-ta-to-chip' flight calls.",
}


def _call_ollama(prompt: str, system_prompt: str, timeout_seconds: float = 8.0) -> Optional[str]:
    """Execute a local query against Ollama's HTTP API."""
    url = f"{settings.ollama_host.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 80,
            "stop": ["\n\n", "User:", "Assistant:"],
        },
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "").strip()
                if response_text:
                    return response_text
    except Exception as e:
        logger.debug("Ollama request failed or server offline (%s): %s", url, e)

    return None


def generate_species_tip(common_name: str, scientific_name: str) -> str:
    """
    Generate a 1-2 sentence grounded tip on what visual mark or sound to look/listen for.
    Must be strictly grounded in verified traits; fallback if offline or unsure.
    """
    system_prompt = (
        "You are an offline field ornithologist assistant. "
        "Provide strictly grounded, factual bird identification tips. "
        "Never hallucinate facts. If unsure, say 'Unsure about field marks.' "
        "Keep your output to exactly 1 or 2 concise sentences (under 40 words total)."
    )
    prompt = (
        f"Species: {common_name} ({scientific_name}). "
        f"What distinctive visual field mark or sound pattern should a birdwatcher look or listen for? "
        f"Reply in 1 or 2 sentences only."
    )

    ollama_result = _call_ollama(prompt, system_prompt)
    if ollama_result:
        return ollama_result

    # Offline curated fallback
    clean_name = common_name.lower().strip()
    for key, tip in CURATED_FIELD_TIPS.items():
        if key in clean_name or clean_name in key:
            return tip

    return (
        f"Watch for distinctive plumage patterns and listen for rhythmic calls in tree branches or low foliage. "
        f"Consult a local field guide to verify distinguishing marks."
    )


def generate_daily_nudge(life_list: List[Dict[str, Any]], month_name: Optional[str] = None) -> str:
    """
    Suggest a short outdoor outing based on the user's recorded life list and the current month.
    """
    current_month = month_name or datetime.now().strftime("%B")
    species_names = [s.get("common_name", "") for s in life_list[:8] if s.get("common_name")]
    species_summary = ", ".join(species_names) if species_names else "none yet"

    system_prompt = (
        "You are an outdoor nature companion encouraging people to step outside and listen for birds. "
        "Keep responses grounded, encouraging, and exactly 1-2 sentences (under 40 words)."
    )
    prompt = (
        f"Month: {current_month}. User's recorded bird species so far: {species_summary}. "
        f"Suggest one short morning or dusk outing: where to go (habitat) and what bird call to listen for. "
        f"Keep to 1-2 sentences."
    )

    ollama_result = _call_ollama(prompt, system_prompt)
    if ollama_result:
        return ollama_result

    # Grounded fallback
    if species_names:
        return (
            f"Step outside near park edges or leafy trees this morning during peak activity. "
            f"Listen for new song patterns beyond the {len(life_list)} species already on your life list."
        )
    return (
        f"Take a 15-minute quiet walk outdoors near woodland edges or neighborhood trees this {current_month}. "
        f"Early morning is the best time to record your very first bird call."
    )


def generate_journal_entry(species_list: List[str], outing_minutes: float) -> str:
    """
    Create a brief 2-sentence field journal note for an outing.
    """
    species_str = ", ".join(species_list) if species_list else "ambient nature"
    system_prompt = (
        "You are a field naturalist recording a short journal log. "
        "Be direct, grounded, and write exactly 1-2 sentences."
    )
    prompt = (
        f"Write a 2-sentence field journal entry for an outing of {round(outing_minutes, 1)} minutes outdoors. "
        f"Identified species: {species_str}."
    )

    ollama_result = _call_ollama(prompt, system_prompt)
    if ollama_result:
        return ollama_result

    return (
        f"Completed a {round(outing_minutes, 1)}-minute outdoor outing with eyes up. "
        f"Recorded audio confirmed: {species_str}."
    )


def check_ollama_status() -> Dict[str, Any]:
    """Check connectivity to the local Ollama instance and model availability."""
    url = f"{settings.ollama_host.rstrip('/')}/api/tags"
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                model_present = any(settings.ollama_model in m for m in models)
                return {
                    "online": True,
                    "target_model": settings.ollama_model,
                    "model_available": model_present,
                    "installed_models": models,
                }
    except Exception as e:
        return {
            "online": False,
            "target_model": settings.ollama_model,
            "model_available": False,
            "error": str(e),
        }

    return {
        "online": False,
        "target_model": settings.ollama_model,
        "model_available": False,
    }
