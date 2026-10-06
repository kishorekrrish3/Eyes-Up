import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.birdnet_service import analyze_audio
from app.config import settings
from app.db import (
    add_sighting,
    get_active_outing,
    get_life_list,
    get_recent_sightings,
    get_touch_grass_stats,
    init_db,
    is_heard_before,
    start_outing,
    stop_outing,
)
from app.llm_service import (
    check_ollama_status,
    generate_daily_nudge,
    generate_journal_entry,
    generate_species_tip,
)
from app.tts_service import synthesize_speech

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title="Eyes Up",
    description="Offline bird-call companion for the Touch Grass challenge",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic schemas for request validation
class StopOutingRequest(BaseModel):
    outing_id: int
    screen_seconds: int = 0


class JournalRequest(BaseModel):
    species_list: List[str]
    outing_minutes: float


@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Eyes Up API is running. Static files not yet deployed."}


@app.post("/api/identify")
async def identify_bird(
    audio: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    outing_id: Optional[int] = Form(None),
    threshold: Optional[float] = Form(None),
):
    """
    Primary endpoint: accepts recorded audio clip, runs offline BirdNET analysis,
    checks life list, generates grounded Gemma tip, and prepares TTS readout.
    """
    conf_threshold = threshold if threshold is not None else settings.birdnet_confidence_threshold
    lat = latitude if latitude is not None else settings.birdnet_latitude
    lon = longitude if longitude is not None else settings.birdnet_longitude

    # Determine file extension
    suffix = ".wav"
    if audio.filename and "." in audio.filename:
        suffix = Path(audio.filename).suffix.lower()

    # Save to temporary file for analysis
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        analysis = analyze_audio(
            audio_path=tmp_path,
            confidence_threshold=conf_threshold,
            latitude=lat,
            longitude=lon,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not analysis.get("success"):
        return {
            "success": False,
            "identified": False,
            "message": analysis.get("message", "Analysis failed"),
            "top_species": None,
            "other_species": [],
            "tts": synthesize_speech("Analysis failed. Please try again."),
        }

    if not analysis.get("identified"):
        speech = synthesize_speech("Couldn't tell, try again.")
        return {
            "success": True,
            "identified": False,
            "message": analysis.get("message", "Couldn't tell, try again."),
            "top_species": None,
            "other_species": [],
            "tts": speech,
        }

    species_list = analysis.get("species", [])
    top = species_list[0]

    # Check life list
    heard_before = is_heard_before(top["scientific_name"])
    is_new = not heard_before

    # Generate grounded Gemma tip (<= 2 sentences)
    tip = generate_species_tip(top["common_name"], top["scientific_name"])

    # Log to database
    add_sighting(
        common_name=top["common_name"],
        scientific_name=top["scientific_name"],
        confidence=top["confidence"],
        latitude=lat,
        longitude=lon,
        outing_id=outing_id,
        tip=tip,
    )

    # Format speech readout
    badge_phrase = "New species!" if is_new else "Heard before."
    readout = (
        f"{top['common_name']}. {int(top['confidence'] * 100)} percent match. "
        f"{badge_phrase} {tip}"
    )
    speech = synthesize_speech(readout)

    top_card = {
        "common_name": top["common_name"],
        "scientific_name": top["scientific_name"],
        "confidence": top["confidence"],
        "confidence_percent": int(top["confidence"] * 100),
        "tip": tip,
        "heard_before": heard_before,
        "is_new": is_new,
    }

    other_cards = [
        {
            "common_name": s["common_name"],
            "scientific_name": s["scientific_name"],
            "confidence": s["confidence"],
            "confidence_percent": int(s["confidence"] * 100),
        }
        for s in species_list[1:3]
    ]

    return {
        "success": True,
        "identified": True,
        "message": analysis.get("message"),
        "top_species": top_card,
        "other_species": other_cards,
        "tts": speech,
    }


@app.get("/api/life-list")
async def get_user_life_list():
    """Retrieve unique logged species and counts."""
    species = get_life_list()
    recent = get_recent_sightings(limit=10)
    return {
        "total_species": len(species),
        "species": species,
        "recent_sightings": recent,
    }


@app.post("/api/outing/start")
async def start_outdoor_outing():
    """Start an outdoor outing to track Touch Grass time."""
    outing_id = start_outing()
    return {"outing_id": outing_id, "status": "active"}


@app.post("/api/outing/stop")
async def stop_outdoor_outing(req: StopOutingRequest):
    """End an outdoor outing and calculate outdoor minutes vs screen minutes."""
    result = stop_outing(req.outing_id, req.screen_seconds)
    if not result:
        raise HTTPException(status_code=404, detail="Outing not found")
    stats = get_touch_grass_stats(days=7)
    return {"outing": result, "weekly_stats": stats}


@app.get("/api/outing/status")
async def check_outing_status():
    """Check if an outing is currently in progress."""
    active = get_active_outing()
    return {"active": active is not None, "outing": active}


@app.get("/api/touch-grass-score")
async def get_touch_grass_score(days: int = 7):
    """Retrieve Touch Grass score (outdoor minutes vs screen minutes)."""
    return get_touch_grass_stats(days=days)


@app.get("/api/daily-nudge")
async def get_daily_nudge():
    """Gemma daily outing nudge based on life list and current season."""
    species = get_life_list()
    nudge = generate_daily_nudge(species)
    return {"nudge": nudge}


@app.post("/api/journal")
async def get_journal_entry(req: JournalRequest):
    """Generate a brief 2-sentence field journal note."""
    entry = generate_journal_entry(req.species_list, req.outing_minutes)
    return {"entry": entry}


@app.get("/api/status")
async def get_system_status():
    """Check health of offline components."""
    ollama_info = check_ollama_status()
    return {
        "app": "Eyes Up",
        "version": "0.1.0",
        "offline_ready": True,
        "birdnet_threshold": settings.birdnet_confidence_threshold,
        "tts_engine": settings.tts_engine,
        "ollama": ollama_info,
    }


# Mount static directory for frontend assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Ensure database is initialized
init_db()
