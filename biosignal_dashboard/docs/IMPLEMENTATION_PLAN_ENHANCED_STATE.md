# Enhanced State Estimation + Remaining Phases – Implementation Plan

## Overview

This plan enhances the current Phase 6 State Estimation with a more robust multimodal approach based on research findings, then completes the remaining phases (Audio, Polish).

### Key Enhancements to State Estimation

| Feature | Current | Enhanced |
|---------|---------|----------|
| EEG Features | Band powers, simple ratios | Engagement Index, θ/α ratio, FAA (optional) |
| ECG/HRV | Basic R-peak detection | Proper RMSSD, SDNN, HR diff from baseline |
| GSR/EDA | Basic SCR count | Tonic (SCL) + Phasic (SCR) decomposition |
| Normalization | None | Z-scores against personal baselines |
| Labels | 6 ad-hoc states | 5 structured states on Focus×Stress grid |
| Calibration | None | Guided baseline calibration wizard |
| Wearables | None | Extensibility hooks for Pixel Watch, rings |

---

## Phase 6A – Enhanced Feature Extraction

### [MODIFY] features_eeg.py

Add new features:
- **Engagement Index**: `beta / (alpha + theta + ε)`
- **Theta/Alpha Ratio**: `theta / (alpha + ε)` – drowsiness indicator
- **Frontal Alpha Asymmetry (FAA)**: `log(alpha_left) - log(alpha_right)` (requires channel awareness)
- Return structured `EEGFeatures` dataclass with all metrics

### [MODIFY] features_gsr.py

Improve EDA decomposition:
- **Tonic SCL**: Mean level + slope (linear regression)
- **Phasic SCR**: Peak detection with amplitude threshold
- **SCR count per minute**: Normalized to 60s window
- Return `EDAFeatures` dataclass

### [MODIFY] features_ecg.py

Improve HRV metrics:
- Use longer window (60s) for HRV calculations
- Proper **RMSSD** from RR intervals (not raw ECG)
- **SDNN** standard deviation of NN intervals
- **Heart Rate** from mean RR
- Better R-peak filtering (300-2000ms RR validity)

---

## Phase 6B – Baseline & Normalization

### [NEW] baseline.py

Create baseline system with `BaselineProfile` dataclass and normalization utilities.
Storage: `baseline_profile.json` in project data directory.

---

## Phase 6C – Enhanced Fusion

### [MODIFY] estimator.py

Restructure fusion with:
1. **Modality Meters** (each 0-1): eeg_focus, hrv_stress, eda_arousal
2. **5-State Labels**: Focused & Calm, Focused but Tense, Relaxed & Unfocused, Overwhelmed, Balanced

---

## Phase 6D – Calibration Wizard (Hardware Gate)

### [NEW] calibration.py + Frontend UI

Calibration flow (~13 min):
- baseline_rest (5 min)
- focused_task (5 min)  
- stress_task (3 min)

---

## Phase 6E – Wearable Extensibility

### [NEW] features_wearables.py

Stub adapter for future Pixel Watch / ring integration.

---

## Phase 7 – Audio Control & Timeline

- AudioTimeline component (canvas-based)
- AudioControls component (file selector, play/pause events)

---

## Phase 8 – Performance & Polish

1. Latency measurement
2. Dispatcher tuning
3. Error handling
4. UX polish (tooltips, legends)
5. Verify launcher script

---

## Implementation Order

1. Phase 6A → 2. Phase 6B → 3. Phase 6C → 4. Phase 6E → 5. Phase 6D → 6. Phase 7 → 7. Phase 8
