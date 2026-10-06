# Eyes Up 🌿

> **An offline bird-call companion that wants you to put the phone away.**  
> Built for the Hacktoberfest 2026 "Touch Grass" Challenge.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![BirdNET](https://img.shields.io/badge/BirdNET-TFLite%20Offline-green.svg)](https://birdnet.cornell.edu/)
[![Ollama](https://img.shields.io/badge/Ollama-Gemma%202--2B-orange.svg)](https://ollama.com/)

---

## The Philosophy: Screen as the Shortest Part

Most nature apps try to keep your eyes glued to glass: endless infinite feeds, social leaderboards, species galleries, and constant push notifications. 

**Eyes Up does the opposite.**

1. Tap **Record** (30s) or start an Outing.
2. Put the phone in your pocket and look up into the canopy.
3. The app records ambient audio, identifies calling birds locally using **BirdNET**, generates a strict 2-sentence field tip using **Gemma**, speaks the result aloud via **Text-to-Speech**, and dims the screen to black.
4. It tracks your **Touch Grass Score**: outdoor minutes versus screen minutes.

**100% Offline. Zero cloud telemetry. Zero subscriptions.**

---

## Architecture at a Glance

- **Bird Acoustic Classification**: Cornell Lab's BirdNET model running locally via Google LiteRT (TFLite CPU delegate).
- **On-Device LLM**: Gemma 2 (2B) running locally via [Ollama](https://ollama.com) for strictly grounded field cues, daily outing nudges, and short journal entries.
- **Backend**: Python FastAPI with SQLite for local sightings and outing tracking.
- **Frontend**: Single-page PWA with client-side 16-bit PCM WAV encoding and Screen-Off pocket mode.
- **Audio Output**: Local Text-to-Speech (native mobile Web Speech API or local `piper`/`espeak`; optional ElevenLabs adapter).

---

## Quickstart

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- (Optional but recommended) [Ollama](https://ollama.com/) for local Gemma tips:
  ```bash
  ollama pull gemma2:2b
  ```

### 2. Install Dependencies
```bash
git clone https://github.com/your-username/eyes-up.git
cd eyes-up

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Launch App
```bash
python run.py
# or: make run
```

Open your browser at `http://localhost:8000`.

---

## Phone Setup for the Field (Trail Ready)

You don't need cellular data or internet on the trail. Here is how to use it outdoors:

### Option A: Laptop in a Backpack + Phone in Pocket (Simplest & Recommended)
1. Turn on your phone's personal Wi-Fi Hotspot (no cellular connection required).
2. Connect your laptop to the hotspot.
3. Run `python run.py` on your laptop. The startup banner displays your local IP (e.g. `http://192.168.43.12:8000`).
4. On your phone's mobile browser (Chrome/Safari), navigate to that IP address.
5. Tap the browser menu and select **"Add to Home Screen"** to install the PWA.
6. Put the laptop in your backpack, and you are fully wireless in the woods!

### Option B: Directly on Android via Termux
Install Python and dependencies inside Termux and run `python run.py` directly on the device, opening `http://localhost:8000` in mobile Chrome.

---

## Airplane Mode Verification

To verify that Eyes Up is truly 100% offline:
1. Disconnect your machine/phone from Ethernet and the internet.
2. Turn on **Airplane Mode**.
3. Open `http://localhost:8000` (or your local hotspot IP).
4. Tap **Record (30s)** or upload `samples/sample_bird.wav`.
5. BirdNET will classify the audio on your CPU, SQLite will store the sighting, and Gemma/Ollama will provide local field cues.

---

## Configuration (`.env`)

A single `.env` file controls all settings without touching code:

| Setting | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | IP interface (0.0.0.0 binds to LAN/hotspot for phones) |
| `PORT` | `8000` | Server port |
| `DATABASE_PATH` | `./data/eyes_up.db` | Local SQLite database file |
| `BIRDNET_CONFIDENCE_THRESHOLD` | `0.50` | Minimum confidence score to accept detection |
| `BIRDNET_LATITUDE` | `None` | Optional latitude for seasonal species filtering |
| `BIRDNET_LONGITUDE` | `None` | Optional longitude for seasonal species filtering |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama HTTP endpoint |
| `OLLAMA_MODEL` | `gemma2:2b` | Ollama model name (e.g. `gemma2:2b`, `gemma3:1b`) |
| `TTS_ENGINE` | `browser` | TTS provider: `browser`, `local_cli`, or `elevenlabs` |
| `ELEVENLABS_API_KEY` | `""` | Optional API key (disabled by default) |

---

## Running Tests

Run the full pytest suite:
```bash
pytest -v
```

All 12 unit and integration tests cover:
- BirdNET audio analysis and low-confidence rejection
- SQLite sightings, life list aggregation, and Touch Grass scoring
- Gemma prompt formatting, field tips, and fallback responses
- FastAPI REST endpoints, outing lifecycle, and audio upload

---

## Limitations

1. **Wind and Ambient Noise**: Phone microphones lack shotgun parabolic reflectors. High wind or heavy traffic noise will lower confidence below the 0.50 threshold (the app will tell you to try again).
2. **Multiple Simultaneous Callers**: BirdNET isolates 3-second segments, but in a chaotic dawn chorus with 6 species singing at once, confidence scores are divided.
3. **Microphone Permissions in Safari**: iOS Safari requires tapping the screen before auto-playing synthesized audio.

---

## Licenses & Credits

- **Eyes Up**: Released under the [MIT License](LICENSE).
- **BirdNET**: Developed by the [Cornell Lab of Ornithology](https://www.birds.cornell.edu/) and Chemnitz University of Technology. Used under the BirdNET academic/open license.
- **Gemma**: Developed by Google DeepMind. Used under the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
