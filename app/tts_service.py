import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
import httpx
from app.config import settings

logger = logging.getLogger("eyes_up.tts")


def synthesize_speech(text: str) -> Dict[str, Any]:
    """
    Handle speech synthesis according to configured TTS_ENGINE.
    Modes:
      - 'browser': Hands off text to frontend Web Speech API (zero install, native mobile voices).
      - 'local_cli': Invokes piper or espeak/espeak-ng locally if installed.
      - 'elevenlabs': Swappable cloud adapter (optional, disabled by default).
    """
    clean_text = text.strip()
    engine = settings.tts_engine.lower()

    if engine == "elevenlabs" and settings.elevenlabs_api_key:
        audio_data = _synthesize_elevenlabs(clean_text)
        if audio_data:
            return {
                "engine": "elevenlabs",
                "audio_base64": audio_data,
                "text": clean_text,
            }
        logger.warning("ElevenLabs synthesis failed; falling back to browser Web Speech.")

    if engine == "local_cli":
        audio_data = _synthesize_local_cli(clean_text)
        if audio_data:
            return {
                "engine": "local_cli",
                "audio_base64": audio_data,
                "text": clean_text,
            }
        logger.info("Local CLI TTS (piper/espeak) not available; falling back to browser.")

    # Default / standard offline path: browser client-side Web Speech
    return {
        "engine": "browser",
        "audio_base64": None,
        "text": clean_text,
    }


def _synthesize_local_cli(text: str) -> Optional[str]:
    """Run local piper or espeak-ng if present on the machine."""
    import base64

    # Check for espeak or espeak-ng
    espeak_cmd = shutil.which("espeak-ng") or shutil.which("espeak")
    if espeak_cmd:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            res = subprocess.run(
                [espeak_cmd, "-w", tmp_path, text],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            if res.returncode == 0 and Path(tmp_path).exists():
                data = Path(tmp_path).read_bytes()
                return base64.b64encode(data).decode("ascii")
        except Exception as e:
            logger.debug("espeak execution failed: %s", e)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return None


def _synthesize_elevenlabs(text: str) -> Optional[str]:
    """Optional swappable ElevenLabs adapter (disabled by default)."""
    import base64

    if not settings.elevenlabs_api_key:
        return None

    voice_id = settings.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default 'Rachel'
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                return base64.b64encode(resp.content).decode("ascii")
            logger.warning("ElevenLabs API error %d: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("ElevenLabs request failed: %s", e)

    return None
