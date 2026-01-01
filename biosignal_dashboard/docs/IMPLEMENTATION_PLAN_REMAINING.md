# Biosignal Dashboard - Remaining Phases Implementation Plan

## Completed ✅
- Phase 1-5: Backend + Frontend base
- Phase 6A-E: Enhanced State Estimation (Engagement Index, HRV, EDA, baselines, wearable stubs)

## Remaining Phases

---

## Phase 6D: Calibration Wizard (Hardware Gate)

> Requires 13+ min user session to build personal baselines

### Backend

#### [NEW] `calibration.py`
- REST endpoints: `/calibration/start`, `/calibration/segment`, `/calibration/stop`
- Segments: `rest` (5 min), `focus` (5 min), `stress` (3 min)
- Compute `BaselineProfile` from segment data
- Save to `baseline_profile.json`

### Frontend

#### [NEW] `CalibrationWizard.tsx`
- Full-screen modal with progress indicator
- Countdown timer for each segment
- Self-rating prompts (focus/stress 1-5)
- "Complete" button saves profile

---

## Phase 7a: System Audio + Session Recording

> MVP: Capture system audio, record sessions to JSONL

### Backend

#### [NEW] `audio/wasapi_capture.py`
- WASAPI loopback capture (Windows)
- Extract loudness (dB) and energy envelope at 10 Hz
- Expose via WebSocket: `audio_level` messages

#### [NEW] `session/recorder.py`
- Session lifecycle: `start_session()`, `stop_session()`
- Record to JSONL (biosignals + audio + state + markers)
- REST: `/session/start`, `/session/stop`, `/session/marker`

### Frontend

#### [NEW] `SessionControls.tsx`
- Start/Stop session button
- Add marker button with text input
- Session duration display, Download session file

---

## Phase 7b: Waveform Visualization

> Precise waveform display using wavesurfer.js

### Frontend

#### [NEW] `WaveformPanel.tsx`
- Uses wavesurfer.js for rendering
- Load waveform from file or pre-analyzed JSON
- Sync playhead with session timeline

---

## Phase 7c: Ableton Live Integration

### OSC Transport Bridge
- OSC server on port 9000
- Listen for `/transport/start`, `/transport/stop`, `/clip/name`

### Max4Live Device (Optional)
- Send audio peaks via WebSocket
- Custom M4L device: `AbletonWaveformBridge.amxd`

---

## Phase 8: Performance & Polish

- Latency measurement (< 150ms)
- Error handling for disconnections
- Tooltips/legends on charts
- Reset logging to INFO

---

## Implementation Order

| Priority | Phase | Est. Effort |
|----------|-------|-------------|
| 1 | 7a: Session Recording | 2-3 hours |
| 2 | 7b: Waveform Display | 1-2 hours |
| 3 | 8: Polish | 1-2 hours |
| 4 | 6D: Calibration | 3-4 hours |
| 5 | 7c: Ableton | 4-6 hours |
