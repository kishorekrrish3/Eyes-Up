import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure LiteRT or tflite_runtime is available for birdnetlib
try:
    import tflite_runtime.interpreter  # noqa: F401
except ModuleNotFoundError:
    try:
        import ai_edge_litert.interpreter
        sys.modules["tflite_runtime"] = __import__("ai_edge_litert")
        sys.modules["tflite_runtime.interpreter"] = ai_edge_litert.interpreter
    except Exception as e:
        logging.warning("Could not alias ai_edge_litert to tflite_runtime: %s", e)

logger = logging.getLogger("eyes_up.birdnet")

_analyzer_instance = None


def get_analyzer():
    """Lazy-load the BirdNET Analyzer singleton."""
    global _analyzer_instance
    if _analyzer_instance is None:
        try:
            from birdnetlib.analyzer import Analyzer
            logger.info("Initializing BirdNET-Analyzer model...")
            _analyzer_instance = Analyzer()
            logger.info("BirdNET-Analyzer model loaded successfully.")
        except Exception as e:
            logger.error("Failed to load BirdNET Analyzer: %s", e)
            raise e
    return _analyzer_instance


def analyze_audio(
    audio_path: str,
    confidence_threshold: float = 0.50,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Analyze an audio recording using BirdNET.
    Returns the top 3 species above confidence_threshold, or a graceful failure message.
    """
    file_path = Path(audio_path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        return {
            "success": False,
            "identified": False,
            "message": "Audio file is empty or missing.",
            "species": [],
            "top_species": None,
        }

    try:
        from birdnetlib import Recording

        analyzer = get_analyzer()
        eval_date = date or datetime.now()

        # We request detections at a lower threshold so we can evaluate noise/near misses
        internal_min_conf = min(0.15, confidence_threshold)

        recording_kwargs: Dict[str, Any] = {
            "min_conf": internal_min_conf,
            "date": eval_date,
        }
        if latitude is not None and longitude is not None:
            recording_kwargs["lat"] = latitude
            recording_kwargs["lon"] = longitude

        recording = Recording(analyzer, str(file_path), **recording_kwargs)
        recording.analyze()

        raw_detections = recording.detections or []
    except Exception as e:
        logger.error("BirdNET analysis error on file %s: %s", audio_path, e)
        return {
            "success": False,
            "identified": False,
            "message": f"Could not analyze audio clip: {str(e)}",
            "species": [],
            "top_species": None,
        }

    if not raw_detections:
        return {
            "success": True,
            "identified": False,
            "message": "Couldn't tell, try again. No bird sounds detected in this clip.",
            "species": [],
            "top_species": None,
        }

    # Aggregate detections across 3-second segments by scientific name (take peak confidence)
    species_map: Dict[str, Dict[str, Any]] = {}
    for d in raw_detections:
        sci_name = d.get("scientific_name", "").strip()
        if not sci_name:
            continue

        conf = float(d.get("confidence", 0.0))
        if sci_name not in species_map or conf > species_map[sci_name]["confidence"]:
            species_map[sci_name] = {
                "common_name": d.get("common_name", sci_name),
                "scientific_name": sci_name,
                "confidence": round(conf, 3),
                "start_time": d.get("start_time", 0.0),
                "end_time": d.get("end_time", 3.0),
            }

    # Sort species by confidence descending
    sorted_species = sorted(species_map.values(), key=lambda s: s["confidence"], reverse=True)

    # Check top detection against the user's confidence threshold
    valid_species = [s for s in sorted_species if s["confidence"] >= confidence_threshold]

    if not valid_species:
        peak_conf = sorted_species[0]["confidence"] if sorted_species else 0.0
        return {
            "success": True,
            "identified": False,
            "message": (
                f"Couldn't tell, try again. Peak match was {sorted_species[0]['common_name']} "
                f"at {int(peak_conf * 100)}% confidence, below the {int(confidence_threshold * 100)}% threshold."
            ),
            "species": [],
            "top_species": None,
        }

    # Take top 3
    top_3 = valid_species[:3]
    top_match = top_3[0]

    return {
        "success": True,
        "identified": True,
        "message": f"Identified {top_match['common_name']} ({int(top_match['confidence'] * 100)}% confidence).",
        "species": top_3,
        "top_species": top_match,
    }
