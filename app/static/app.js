// Eyes Up - Offline Bird-Call Companion Frontend Logic

let isRecording = false;
let recordTimeout = null;
let recordInterval = null;
let secondsRemaining = 30;
let audioContext = null;
let mediaStream = null;
let audioProcessor = null;
let audioChunks = [];
let sampleRate = 44100;

// Outing and Touch Grass State
let currentOutingId = null;
let outingStartTime = null;
let outingTimerInterval = null;
let screenSeconds = 0;
let screenTimerInterval = null;
let screenOffMode = false;
let lastResultSpeech = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initOutingState();
  initVisibilityTracking();
  loadDailyNudge();
  loadTouchGrassScore();
  loadLifeList();
  registerServiceWorker();

  // Attach event listeners
  document.getElementById("btn-record").addEventListener("click", toggleRecording);
  document.getElementById("btn-outing").addEventListener("click", toggleOuting);
  document.getElementById("btn-screen-off").addEventListener("click", toggleScreenOffMode);
  document.getElementById("screen-off-overlay").addEventListener("click", dismissScreenOff);
  document.getElementById("btn-toggle-list").addEventListener("click", toggleLifeList);
  document.getElementById("btn-replay-tts").addEventListener("click", replayTTS);

  // File upload fallback
  const fileInput = document.getElementById("audio-file-input");
  document.getElementById("upload-link").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", handleFileUpload);
});

// Service Worker for offline PWA
function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js").catch((err) => {
      console.log("SW registration notice:", err);
    });
  }
}

// --------------------------------------------------------------------------
// Audio Recording & WAV Encoding (Pure JS - No server ffmpeg dependency)
// --------------------------------------------------------------------------
async function toggleRecording() {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
}

async function startRecording() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    alert("Microphone access is required to identify birds: " + err.message);
    return;
  }

  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  sampleRate = audioContext.sampleRate;
  const source = audioContext.createMediaStreamSource(mediaStream);

  // Buffer size 4096 mono
  audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);
  audioChunks = [];

  audioProcessor.onaudioprocess = (e) => {
    if (!isRecording) return;
    const inputData = e.inputBuffer.getChannelData(0);
    audioChunks.push(new Float32Array(inputData));
  };

  source.connect(audioProcessor);
  audioProcessor.connect(audioContext.destination);

  isRecording = true;
  secondsRemaining = 30;

  const btnRecord = document.getElementById("btn-record");
  const wrapper = document.querySelector(".record-btn-wrapper");
  btnRecord.classList.add("recording");
  wrapper.classList.add("is-recording");
  document.getElementById("record-timer").textContent = `${secondsRemaining}s`;

  showAnalyzingState(false);
  document.getElementById("result-empty").style.display = "flex";
  document.getElementById("result-empty").innerHTML = "<span>Recording ambient audio... (tap to finish early)</span>";

  // Countdown timer
  recordInterval = setInterval(() => {
    secondsRemaining--;
    if (secondsRemaining <= 0) {
      stopRecording();
    } else {
      document.getElementById("record-timer").textContent = `${secondsRemaining}s`;
    }
  }, 1000);
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;

  clearInterval(recordInterval);
  const btnRecord = document.getElementById("btn-record");
  const wrapper = document.querySelector(".record-btn-wrapper");
  btnRecord.classList.remove("recording");
  wrapper.classList.remove("is-recording");
  document.getElementById("record-timer").textContent = "30s";

  if (audioProcessor) {
    audioProcessor.disconnect();
    audioProcessor = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
  if (audioContext && audioContext.state !== "closed") {
    audioContext.close();
  }

  // Encode collected PCM audio into standard 16-bit PCM WAV
  const wavBlob = encodeWAV(audioChunks, sampleRate);
  sendAudioForIdentification(wavBlob);
}

function encodeWAV(chunks, sampleRate) {
  let totalLength = 0;
  for (let i = 0; i < chunks.length; i++) {
    totalLength += chunks[i].length;
  }

  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (let i = 0; i < chunks.length; i++) {
    merged.set(chunks[i], offset);
    offset += chunks[i].length;
  }

  // Create 16-bit PCM WAV buffer
  const buffer = new ArrayBuffer(44 + merged.length * 2);
  const view = new DataView(buffer);

  // RIFF identifier
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + merged.length * 2, true);
  writeString(view, 8, "WAVE");

  // fmt subchunk
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
  view.setUint16(22, 1, true); // NumChannels (1 = mono)
  view.setUint32(24, sampleRate, true); // SampleRate
  view.setUint32(28, sampleRate * 2, true); // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
  view.setUint16(32, 2, true); // BlockAlign (NumChannels * BitsPerSample/8)
  view.setUint16(34, 16, true); // BitsPerSample (16 bits)

  // data subchunk
  writeString(view, 36, "data");
  view.setUint32(40, merged.length * 2, true);

  // Write PCM samples (convert float -1..1 to int16 -32768..32767)
  let pcmOffset = 44;
  for (let i = 0; i < merged.length; i++, pcmOffset += 2) {
    let s = Math.max(-1, Math.min(1, merged[i]));
    view.setInt16(pcmOffset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

// --------------------------------------------------------------------------
// Identification API Request & Card Rendering
// --------------------------------------------------------------------------
async function sendAudioForIdentification(audioBlob) {
  showAnalyzingState(true);

  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.wav");
  if (currentOutingId) {
    formData.append("outing_id", currentOutingId);
  }

  try {
    const res = await fetch("/api/identify", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    renderResultCard(data);
  } catch (err) {
    console.error("Identification failed:", err);
    renderErrorCard("Connection to local server failed. Please ensure the app is running.");
  } finally {
    showAnalyzingState(false);
  }
}

function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  sendAudioForIdentification(file);
}

function showAnalyzingState(isAnalyzing) {
  const emptyState = document.getElementById("result-empty");
  const analyzingState = document.getElementById("result-analyzing");
  const contentState = document.getElementById("result-content");

  if (isAnalyzing) {
    emptyState.style.display = "none";
    contentState.style.display = "none";
    analyzingState.style.display = "flex";
  } else {
    analyzingState.style.display = "none";
  }
}

function renderResultCard(data) {
  const emptyState = document.getElementById("result-empty");
  const contentState = document.getElementById("result-content");

  if (!data || !data.identified) {
    emptyState.style.display = "flex";
    contentState.style.display = "none";
    const msg = data ? data.message : "Couldn't tell, try again.";
    emptyState.innerHTML = `<span><strong>${msg}</strong><br><small>Try getting closer or waiting for ambient quiet.</small></span>`;
    speakTTS(data ? data.tts : { engine: "browser", text: "Couldn't tell, try again." });
    triggerScreenOffIfEnabled();
    return;
  }

  const top = data.top_species;
  document.getElementById("card-common-name").textContent = top.common_name;
  document.getElementById("card-scientific-name").textContent = top.scientific_name;
  document.getElementById("card-conf-badge").textContent = `${top.confidence_percent}% match`;

  const newBadge = document.getElementById("card-new-badge");
  if (top.is_new) {
    newBadge.className = "new-badge";
    newBadge.textContent = "NEW SPECIES!";
  } else {
    newBadge.className = "heard-badge";
    newBadge.textContent = "Heard before";
  }

  document.getElementById("card-tip").textContent = top.tip;

  // Other probable species
  const chipsContainer = document.getElementById("card-other-chips");
  chipsContainer.innerHTML = "";
  if (data.other_species && data.other_species.length > 0) {
    chipsContainer.innerHTML = "<span style='margin-right:2px;'>Also possible:</span>";
    data.other_species.forEach((s) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = `${s.common_name} (${s.confidence_percent}%)`;
      chipsContainer.appendChild(chip);
    });
  }

  emptyState.style.display = "none";
  contentState.style.display = "flex";

  // Cache speech and speak
  lastResultSpeech = data.tts;
  speakTTS(data.tts);

  // Refresh stats
  loadLifeList();
  loadTouchGrassScore();

  triggerScreenOffIfEnabled();
}

function renderErrorCard(message) {
  const emptyState = document.getElementById("result-empty");
  const contentState = document.getElementById("result-content");
  contentState.style.display = "none";
  emptyState.style.display = "flex";
  emptyState.innerHTML = `<span style="color: var(--danger-red);">${message}</span>`;
}

// --------------------------------------------------------------------------
// TTS Engine Handler
// --------------------------------------------------------------------------
function speakTTS(ttsData) {
  if (!ttsData) return;

  if (ttsData.audio_base64) {
    try {
      const audio = new Audio("data:audio/wav;base64," + ttsData.audio_base64);
      audio.play();
      return;
    } catch (e) {
      console.warn("Base64 audio playback failed, falling back to speech synthesis:", e);
    }
  }

  if (ttsData.text && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(ttsData.text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  }
}

function replayTTS() {
  if (lastResultSpeech) {
    speakTTS(lastResultSpeech);
  }
}

// --------------------------------------------------------------------------
// Screen-Off Mode
// --------------------------------------------------------------------------
function toggleScreenOffMode() {
  screenOffMode = !screenOffMode;
  const btn = document.getElementById("btn-screen-off");
  if (screenOffMode) {
    btn.classList.add("active");
    btn.textContent = "Screen-Off: ON";
  } else {
    btn.classList.remove("active");
    btn.textContent = "Screen-Off: OFF";
  }
}

function triggerScreenOffIfEnabled() {
  if (screenOffMode) {
    const overlay = document.getElementById("screen-off-overlay");
    overlay.classList.add("active");
  }
}

function dismissScreenOff() {
  const overlay = document.getElementById("screen-off-overlay");
  overlay.classList.remove("active");
}

// --------------------------------------------------------------------------
// Touch Grass & Outing Tracking
// --------------------------------------------------------------------------
function initOutingState() {
  const storedId = localStorage.getItem("eyes_up_outing_id");
  const storedStart = localStorage.getItem("eyes_up_outing_start");
  if (storedId && storedStart) {
    currentOutingId = parseInt(storedId, 10);
    outingStartTime = new Date(storedStart);
    setOutingUIActive(true);
    startOutingTimer();
  }
}

function initVisibilityTracking() {
  // Track screen time when page is visible
  setInterval(() => {
    if (document.visibilityState === "visible") {
      screenSeconds++;
    }
  }, 1000);
}

async function toggleOuting() {
  if (currentOutingId) {
    await endOuting();
  } else {
    await startOuting();
  }
}

async function startOuting() {
  try {
    const res = await fetch("/api/outing/start", { method: "POST" });
    const data = await res.json();
    currentOutingId = data.outing_id;
    outingStartTime = new Date();
    localStorage.setItem("eyes_up_outing_id", currentOutingId);
    localStorage.setItem("eyes_up_outing_start", outingStartTime.toISOString());
    screenSeconds = 0;
    setOutingUIActive(true);
    startOutingTimer();
  } catch (err) {
    console.error("Start outing error:", err);
  }
}

async function endOuting() {
  if (!currentOutingId) return;

  try {
    await fetch("/api/outing/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        outing_id: currentOutingId,
        screen_seconds: screenSeconds,
      }),
    });
  } catch (err) {
    console.error("Stop outing error:", err);
  }

  currentOutingId = null;
  outingStartTime = null;
  localStorage.removeItem("eyes_up_outing_id");
  localStorage.removeItem("eyes_up_outing_start");
  clearInterval(outingTimerInterval);
  setOutingUIActive(false);
  loadTouchGrassScore();
}

function setOutingUIActive(active) {
  const btn = document.getElementById("btn-outing");
  if (active) {
    btn.classList.add("in-progress");
    btn.textContent = "End Outing";
  } else {
    btn.classList.remove("in-progress");
    btn.textContent = "Start Outing";
  }
}

function startOutingTimer() {
  clearInterval(outingTimerInterval);
  outingTimerInterval = setInterval(() => {
    if (!outingStartTime) return;
    const elapsedMinutes = Math.floor((new Date() - outingStartTime) / 60000);
    const btn = document.getElementById("btn-outing");
    btn.textContent = `End Outing (${elapsedMinutes}m)`;
  }, 15000);
}

async function loadTouchGrassScore() {
  try {
    const res = await fetch("/api/touch-grass-score");
    const data = await res.json();
    const scoreElem = document.getElementById("touch-grass-score");
    if (data.outdoor_minutes > 0) {
      scoreElem.textContent = `${data.ratio}x (${data.eyes_up_percentage}% eyes up)`;
    } else {
      scoreElem.textContent = "0m outdoors (Ready)";
    }
  } catch (err) {
    console.error("Touch grass score fetch error:", err);
  }
}

// --------------------------------------------------------------------------
// Life List & Daily Nudge
// --------------------------------------------------------------------------
async function loadDailyNudge() {
  try {
    const res = await fetch("/api/daily-nudge");
    const data = await res.json();
    if (data.nudge) {
      document.getElementById("nudge-text").textContent = data.nudge;
    }
  } catch (err) {
    console.error("Nudge fetch error:", err);
  }
}

async function loadLifeList() {
  try {
    const res = await fetch("/api/life-list");
    const data = await res.json();
    document.getElementById("life-list-count").textContent = `${data.total_species} species`;

    const itemsContainer = document.getElementById("life-list-items");
    itemsContainer.innerHTML = "";
    if (!data.species || data.species.length === 0) {
      itemsContainer.innerHTML = "<div style='color: #64748b; font-size: 0.8rem;'>No species logged yet. Tap Record outside!</div>";
      return;
    }

    data.species.forEach((s) => {
      const row = document.createElement("div");
      row.className = "life-list-row";
      row.innerHTML = `
        <div>
          <strong>${s.common_name}</strong>
          <span style="color:#64748b; font-size:0.75rem; margin-left:4px;">(${s.total_heard}x)</span>
        </div>
        <span style="color:#10b981; font-weight:600;">${Math.round(s.max_confidence * 100)}%</span>
      `;
      itemsContainer.appendChild(row);
    });
  } catch (err) {
    console.error("Life list fetch error:", err);
  }
}

function toggleLifeList() {
  const panel = document.getElementById("life-list-panel");
  panel.classList.toggle("open");
}
