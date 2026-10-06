---
title: Eyes Up: an offline bird-call companion that wants you to put the phone away
published:
tags: devchallenge, hf26challenge
---
*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

I love birding, but I despise modern birding apps.

The moment you open most wildlife apps on a trail, they demand your full visual attention. You get feeds, social leaderboards, uncompressed photo galleries, and notifications begging you to log into an account. Before you know it, you're standing under a 100-year-old oak tree staring at blue light instead of looking up at the bird singing directly above you.

I built **Eyes Up** to solve that problem. It is an offline, privacy-first bird-call companion built specifically for the "Touch Grass" challenge.

The entire interface is designed around a single constraint: **the screen should be the shortest part of the experience.**

You tap one big button—"Record (30s)"—and drop your phone into your jacket pocket. The app records the acoustic environment, runs Cornell's BirdNET classifier locally on your device's CPU, prompts an on-device Gemma 2 model via Ollama to generate a strictly grounded two-sentence field tip, and speaks the result aloud via Text-to-Speech:

> *"Heard American Robin, 91% match. New species! Look for a warm brick-red breast on lawns and listen for a cheerful caroling song."*

Then it dims the screen to pitch black.

There is no infinite scroll. There are no friend feeds. There is only a single result card, an offline life list, and a **Touch Grass Score** that tracks how many minutes you spent outdoors versus how many minutes you spent looking at the glass.

## Demo

Here is the one-screen workflow in action:

1. **The Field Dashboard**: Dark charcoal palette (`#0b0f12`) optimized for sunlight visibility. A single 130px record button and a Touch Grass ratio meter.
2. **Screen-Off Pocket Mode**: Once triggered, the app speaks the identification aloud and drops into a full OLED black screen that ignores accidental pocket taps.
3. **The Result Card**: Exactly one card displaying the common name, scientific name, confidence score, a "NEW SPECIES!" badge, and Gemma's concise field cue.

<!-- Outdoor test media placeholders -->
- **App Screenshot**: [TODO: Insert link to screenshot of the single result card on your phone]
- **Field Video / Audio Clip**: [TODO: Insert 15-second video link showing phone in pocket speaking bird ID on trail]

## Code

The complete source code is open-source under the MIT license:

- **Repository**: [https://github.com/kishorekrrish3/Eyes-Up](https://github.com/kishorekrrish3/Eyes-Up)
- **Stack**: Python 3.12, FastAPI, SQLite, BirdNET-Analyzer (Google LiteRT TFLite runtime), Ollama (Gemma 2: 2B), Vanilla HTML5/JS PWA.

To run it locally in one command:

```bash
git clone https://github.com/kishorekrrish3/Eyes-Up.git
cd Eyes-Up
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## How I Built It

I kept the stack lean, fast, and completely free of cloud subscriptions.

### 1. In-Browser 16-Bit PCM WAV Encoding
Mobile browsers record audio in WebM/Opus (Android) or AAC/MP4 (iOS). Decoding those on a lightweight local server usually requires dragging in heavy `ffmpeg` binaries. Instead, I wrote a 40-line client-side audio encoder in `app/static/app.js` using the Web Audio API. The phone samples the raw Float32 microphone data and compiles an uncompressed 16-bit PCM WAV directly in browser memory before uploading. It works identically across mobile Safari and mobile Chrome with zero server codec friction.

### 2. Cornell BirdNET on LiteRT (TFLite CPU)
For acoustic classification, Eyes Up uses the official BirdNET V2.4 model (`BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite`).
- **Model Size**: 61.1 MB.
- **Inference Latency**: ~1.4 seconds on a standard laptop CPU for a 30-second recording (chunked into 3-second segments).
- **RAM Footprint**: ~420 MB resident memory.
- **Filtering**: Detections are aggregated by scientific name, taking peak confidence. Anything under 50% confidence is rejected with a graceful failure: *"Couldn't tell, try again. Try moving closer or waiting for ambient quiet."*

### 3. Strictly Grounded Tips via Gemma 2 (2B)
I used Gemma 2 (2B) through Ollama (`http://localhost:11434`) with strict bounding instructions:
- **Species Tip**: Exactly 1 to 2 sentences (under 40 words) describing the visual field mark or sound pattern to look/listen for. If the model isn't certain, it is instructed to say "Unsure" rather than inventing plumage traits.
- **Daily Outing Nudge**: Synthesizes the user's logged life list and the current calendar month to suggest a 15-minute habitat outing (e.g., *"Step outside near park edges this October morning; listen for white-throated sparrows arriving for winter"*).
- **Offline Resilience**: If Ollama is not running in the field, a curated offline ornithology dictionary steps in seamlessly.

### 4. Touch Grass Outing Tracker
The backend logs outings in a local SQLite database (`data/eyes_up.db`). While an outing is active, the frontend monitors the browser `document.visibilityState`. If your phone screen is on, screen seconds accumulate. If the phone is locked or in your pocket, screen time stops while outdoor outing time ticks forward. Your weekly Touch Grass Score is computed as:
$$\text{Touch Grass Ratio} = \frac{\text{Minutes Outdoors}}{\max(\text{Minutes Screen On}, 0.5)}$$
If you spent 45 minutes walking through the woods and only looked at your phone for 2 minutes to confirm two sightings, your score is **22.5x (96% Eyes Up)**.

## Why Does Open Innovation Matter?

During this build, the contrast between open-source edge AI and proprietary closed cloud APIs could not have been starker.

1. **Zero Signal on the Trail**: If you hike into a ravine or a national forest, cloud APIs fail instantly. A 404 or connection timeout when you hear a rare warbler ruins the entire experience. Because BirdNET and Gemma run locally on hardware in your pocket, Eyes Up works at full speed in dead zones and airplane mode.
2. **Absolute Privacy**: Many modern apps upload continuous microphone streams to third-party cloud servers for processing. In Eyes Up, your audio never leaves your machine. Your life list, GPS coordinates, and recordings stay in your local SQLite database.
3. **Zero Marginal Cost**: Cloud audio transcription and proprietary LLM endpoints charge per minute and per token. Running BirdNET and Gemma locally costs exactly \$0.00 forever.
4. **Model Freedom**: If you want to run Gemma 3 1B on a low-power handheld or step up to Gemma 2 9B on a beefier workstation, you change one line in `.env` (`OLLAMA_MODEL=gemma2:9b`). No vendor lock-in.

## My Agent Session

{% agent_session 586 %}

*View interactive session transcript on DEV:* [Eyes Up: Building an Offline Bird-Call Companion with BirdNET & Gemma](https://dev.to/agent_sessions/eyes-up-building-an-offline-bird-call-companion-with-birdnet-gemma-dmbxhi)

I built Eyes Up using the **Antigravity** coding assistant.

The agentic pairing workflow excelled at eliminating the boilerplate that usually slows down hackathons:
- **Resolving TFLite on Windows Python 3.12**: When standard `tflite-runtime` wheels were missing for Windows, the agent diagnosed the dependency tree and wired Google's modern `ai-edge-litert` package as a clean, transparent shim for `birdnetlib`.
- **In-Memory Audio Engineering**: Instead of having me fiddle with server-side `ffmpeg` installations, the agent implemented the browser PCM WAV encoder from first principles, ensuring portable mobile recording.
- **Comprehensive Verification**: The agent generated a test suite covering the BirdNET wrapper, confidence thresholds, SQLite life-list aggregation, and FastAPI route responses—verifying all 12 unit tests passed green before wrapping up.

<!-- Outdoor field session notes -->
### Real Outdoor Test Log
- **Location**: [TODO: e.g. Highbridge Park, Northern Trail / Local neighborhood woods]
- **Weather / Conditions**: [TODO: e.g. 58°F, overcast, slight breeze]
- **Birds Heard & Identified**: [TODO: List species identified, e.g. Blue Jay (89%), Tufted Titmouse (76%)]
- **What Failed / Surprises**: [TODO: e.g. A passing diesel truck tripped the noise rejection threshold; Gemma's tip about chickadee bibs was spot on]
- **Battery Impact**: [TODO: e.g. 4% battery consumed over a 25-minute outing]

## Prize Categories

- **Best Use of Gemma**: Eyes Up relies on Gemma 2 (2B) running on-device via Ollama for three tightly bounded, high-value tasks: distilling complex ornithological field marks into 2-sentence actionable visual cues, crafting personalized seasonal outing nudges from the user's SQLite life list, and generating offline field journal entries.
- *(Note on ElevenLabs)*: An optional, swappable adapter for ElevenLabs TTS is implemented in `app/tts_service.py` for users desiring hyper-realistic cloud voices, but the app defaults to 100% offline local TTS to honor the Touch Grass ethos.
