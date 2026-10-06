# Eyes Up: Outdoor Field Test Checklist 🌲

Use this 1-page protocol for your 20–30 minute outdoor field trial.

---

## 1. Pre-Outing Gear & Setup Checklist (Before Leaving the Door)

- [ ] **Laptop Battery**: Charged to $\ge 80\%$.
- [ ] **Phone Battery**: Note starting percentage: `____%`.
- [ ] **Offline Check**: Ensure Ollama is running (`ollama serve`) with `gemma2:2b` cached.
- [ ] **Hotspot Link**:
  1. Enable Phone Wi-Fi Hotspot.
  2. Connect laptop to phone hotspot.
  3. Run `python run.py` on laptop.
  4. Open the shown IP address (e.g. `http://192.168.43.12:8000`) in phone browser.
  5. Add to Home Screen (or bookmark).
- [ ] **Airplane Mode / Cellular Off**: Toggle Cellular Data OFF on phone. Verify the app still records, analyzes, and speaks offline.
- [ ] **Stow Laptop**: Place laptop in backpack or shoulder bag with sleep-on-lid disabled (or lid slightly ajar).

---

## 2. 20–30 Minute Trail Protocol

1. **Step Outside & Tap "Start Outing"**: Note the start time.
2. **Pocket the Phone**: Keep your eyes up on tree branches, hedgerows, and shrubs.
3. **When You Hear a Call**:
   - Pull out phone, tap **"RECORD (30s)"**.
   - Point the phone mic gently toward the sound and drop it back into your pocket.
   - Listen for the audio readout via TTS.
   - Notice whether the Gemma tip helps you spot the bird in the foliage.
4. **Try a Noisy Moment**: Test recording near light wind or distant traffic to verify the confidence threshold rejects noise gracefully.
5. **Finish**: Tap **"End Outing"** to lock in your Touch Grass Score.

---

## 3. Field Observation Log Sheet

| # | Time | What You Heard With Ears | BirdNET Identified | Conf % | Latency (sec) | Gemma Tip Helpful? | Notes / Noise (Wind, Traffic) |
|---|---|---|---|---|---|---|---|
| 1 | : | | | % | s | [ ] Yes [ ] No | |
| 2 | : | | | % | s | [ ] Yes [ ] No | |
| 3 | : | | | % | s | [ ] Yes [ ] No | |
| 4 | : | | | % | s | [ ] Yes [ ] No | |
| 5 | : | | | % | s | [ ] Yes [ ] No | |

---

## 4. Post-Outing Debrief & Metrics

- [ ] **Total Outing Duration**: `_____` minutes.
- [ ] **Screen Time Logged**: `_____` minutes.
- [ ] **Touch Grass Score**: `_____x` ratio (`____%` Eyes Up).
- [ ] **Ending Phone Battery**: `____%` (Total drain: `____%`).
- [ ] **Ending Laptop Battery**: `____%` (Total drain: `____%`).
- [ ] **Database Inspection**: Run `python -c "from app.db import get_life_list; print(get_life_list())"` to confirm records were saved to SQLite.

---

## 5. Failure & Friction Review

- **False Positives / Misidentifications**: Did BirdNET guess a bird that clearly wasn't there?
- **Near Misses**: Did the app say "Couldn't tell, try again" on a quiet call?
- **Hardware Friction**: Did the phone screen stay awake or trigger accidental pocket touches?
- **Audio Readout Clarity**: Was the volume loud enough outdoors without earbuds?

*Take the observations from sections 3, 4, and 5 and fill in the `[TODO: ...]` placeholders in `POST.md` before publishing!*
