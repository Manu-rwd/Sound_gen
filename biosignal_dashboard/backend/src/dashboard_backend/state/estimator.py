"""State estimator - combines biosignal features into focus/stress scores.

Enhanced with:
- Modality meters (EEG focus, HRV stress, EDA arousal)
- Baseline normalization
- 5-state labeling (Focus×Stress grid)
- Wearable extensibility
- EMA smoothing

Runs at 1 Hz, computing features from buffered samples and broadcasting state updates.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable
import numpy as np

from ..models.messages import StateScores, StateEstimate
from .features_eeg import compute_eeg_features, EEGFeatures
from .features_gsr import compute_eda_features, EDAFeatures
from .features_ecg import compute_hrv_features, HRVFeatures
from .baseline import (
    BaselineProfile, 
    NormalizedFeatures,
    create_default_baseline, 
    load_baseline,
    normalize_features,
)
from .features_wearables import WearableFeatureAdapter

logger = logging.getLogger(__name__)


# 5-State labels based on Focus×Stress grid
STATE_LABELS = {
    ("high", "low"): "Focused & Calm",
    ("high", "mid"): "Focused",
    ("high", "high"): "Focused but Tense",
    ("mid", "low"): "Balanced",
    ("mid", "mid"): "Balanced / Mixed",
    ("mid", "high"): "Tense",
    ("low", "low"): "Relaxed & Unfocused",
    ("low", "mid"): "Unfocused",
    ("low", "high"): "Overwhelmed",
}


class ExponentialSmoother:
    """Exponential moving average smoother for score stability."""
    
    def __init__(self, alpha: float = 0.3, initial: float = 0.5):
        """
        Args:
            alpha: Smoothing factor (0-1). Higher = less smoothing.
            initial: Initial value before any updates.
        """
        self._alpha = alpha
        self._value = initial
    
    def update(self, new_value: float) -> float:
        """Update and return smoothed value."""
        self._value = self._alpha * new_value + (1 - self._alpha) * self._value
        return self._value
    
    @property
    def value(self) -> float:
        return self._value
    
    def reset(self, value: float = 0.5) -> None:
        self._value = value


class StateEstimator:
    """
    Estimates cognitive/emotional state from multimodal biosignal features.
    
    Combines EEG, GSR/EDA, ECG/HRV, and optional wearable features to compute:
    - Focus score (0-100): Primarily from EEG engagement index
    - Stress score (0-100): From EDA arousal + HRV stress indicators
    
    Uses baseline normalization for personalized scoring.
    Runs at 1 Hz and broadcasts StateEstimate messages.
    """
    
    def __init__(
        self,
        update_interval: float = 1.0,
        eeg_window_seconds: float = 4.0,
        gsr_window_seconds: float = 10.0,  # Reduced from 60s for faster response
        ecg_window_seconds: float = 10.0,  # Reduced from 60s for faster response
        baseline_path: Optional[str] = None,
        smoothing_alpha: float = 0.3,
    ):
        """
        Initialize state estimator.
        
        Args:
            update_interval: How often to compute state (seconds)
            eeg_window_seconds: Window size for EEG analysis (4s recommended)
            gsr_window_seconds: Window size for EDA analysis (60s for SCR)
            ecg_window_seconds: Window size for HRV analysis (60s for RMSSD)
            baseline_path: Path to baseline JSON (uses default if None)
            smoothing_alpha: EMA smoothing factor (0.3 = moderate smoothing)
        """
        self._update_interval = update_interval
        self._eeg_window = eeg_window_seconds
        self._gsr_window = gsr_window_seconds
        self._ecg_window = ecg_window_seconds
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks for state updates
        self._callbacks: List[Callable] = []
        
        # Data buffers
        self._eeg_buffer: List[np.ndarray] = []
        self._gsr_buffer: List[np.ndarray] = []
        self._ecg_buffer: List[np.ndarray] = []
        
        # Sampling rates
        self._eeg_rate: float = 256.0
        self._gsr_rate: float = 50.0
        self._ecg_rate: float = 250.0
        
        # Load or create baseline
        self._baseline = load_baseline() or create_default_baseline()
        logger.info(f"Baseline loaded: {self._baseline.notes or 'default'}")
        
        # Smoothers for output scores
        self._focus_smoother = ExponentialSmoother(smoothing_alpha, 50.0)
        self._stress_smoother = ExponentialSmoother(smoothing_alpha, 50.0)
        
        # Wearable adapter (stub for now)
        self._wearable_adapter = WearableFeatureAdapter()
        
        # Last computed features for debugging
        self._last_features: Dict[str, any] = {}
        self._last_normalized: Optional[NormalizedFeatures] = None
    
    def register_callback(self, callback: Callable) -> None:
        """Register a callback to receive state updates."""
        self._callbacks.append(callback)
    
    def set_baseline(self, baseline: BaselineProfile) -> None:
        """Update the baseline profile."""
        self._baseline = baseline
        logger.info("Baseline profile updated")
    
    # =========================================================================
    # Data input methods
    # =========================================================================
    
    def push_eeg_data(self, data: np.ndarray, sampling_rate: float = 256.0) -> None:
        """Push EEG samples to buffer."""
        self._eeg_rate = sampling_rate
        self._eeg_buffer.append(data)
        max_samples = int(self._eeg_window * sampling_rate)
        self._trim_buffer(self._eeg_buffer, max_samples)
    
    def push_gsr_data(self, data: np.ndarray, sampling_rate: float = 50.0) -> None:
        """Push GSR/EDA samples to buffer."""
        self._gsr_rate = sampling_rate
        self._gsr_buffer.append(data)
        max_samples = int(self._gsr_window * sampling_rate)
        self._trim_buffer(self._gsr_buffer, max_samples)
    
    def push_ecg_data(self, data: np.ndarray, sampling_rate: float = 250.0) -> None:
        """Push ECG samples to buffer."""
        self._ecg_rate = sampling_rate
        self._ecg_buffer.append(data)
        max_samples = int(self._ecg_window * sampling_rate)
        self._trim_buffer(self._ecg_buffer, max_samples)
    
    def _trim_buffer(self, buffer: List[np.ndarray], max_samples: int) -> None:
        """Trim buffer to max samples."""
        if not buffer:
            return
        total = sum(len(arr) for arr in buffer)
        while total > max_samples and len(buffer) > 1:
            removed = buffer.pop(0)
            total -= len(removed)
    
    def _get_concatenated(self, buffer: List[np.ndarray]) -> np.ndarray:
        """Concatenate buffer arrays into single array."""
        if not buffer:
            return np.array([])
        return np.concatenate(buffer)
    
    # =========================================================================
    # Lifecycle methods
    # =========================================================================
    
    async def start(self) -> None:
        """Start the state estimation loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("StateEstimator started")
    
    async def stop(self) -> None:
        """Stop the state estimation loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("StateEstimator stopped")
    
    async def _loop(self) -> None:
        """Main estimation loop running at 1 Hz."""
        while self._running:
            try:
                state = self._compute_state()
                
                for callback in self._callbacks:
                    try:
                        callback(state)
                    except Exception as e:
                        logger.error(f"State callback error: {e}")
                
                await asyncio.sleep(self._update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"StateEstimator loop error: {e}")
                await asyncio.sleep(self._update_interval)
    
    # =========================================================================
    # Core computation
    # =========================================================================
    
    def _compute_state(self) -> StateEstimate:
        """Compute current state from buffered data."""
        
        # === Extract raw features ===
        raw_features: Dict[str, float] = {}
        
        # EEG features
        eeg_features = self._extract_eeg_features()
        if eeg_features:
            raw_features["engagement_index"] = eeg_features.engagement_index
            raw_features["theta_alpha_ratio"] = eeg_features.theta_alpha_ratio
            raw_features["alpha_beta_ratio"] = eeg_features.alpha_beta_ratio
            raw_features["eeg_quality"] = eeg_features.quality_score
        
        # EDA/GSR features
        eda_features = self._extract_eda_features()
        if eda_features:
            raw_features["scl_mean"] = eda_features.scl_mean
            raw_features["scr_count_per_min"] = eda_features.scr_count_per_min
            raw_features["scl_slope"] = eda_features.scl_slope
            raw_features["eda_quality"] = eda_features.quality_score
        
        # HRV/ECG features
        hrv_features = self._extract_hrv_features()
        if hrv_features:
            raw_features["heart_rate"] = hrv_features.heart_rate
            raw_features["rmssd"] = hrv_features.rmssd
            raw_features["sdnn"] = hrv_features.sdnn
            raw_features["hrv_quality"] = hrv_features.quality_score
        
        # Wearable features (if any)
        wearable_features = self._wearable_adapter.compute()
        raw_features.update(wearable_features)
        
        self._last_features = raw_features
        
        # === Normalize features ===
        normalized = normalize_features(raw_features, self._baseline)
        self._last_normalized = normalized
        
        # === Compute modality meters ===
        eeg_focus_meter = self._compute_eeg_focus_meter(normalized, eeg_features)
        hrv_stress_meter = self._compute_hrv_stress_meter(normalized, hrv_features)
        eda_arousal_meter = self._compute_eda_arousal_meter(normalized, eda_features)
        
        # Debug: log feature extraction and meters
        logger.debug(
            f"Features: EEG={eeg_features is not None}, "
            f"EDA={eda_features is not None}, "
            f"HRV={hrv_features is not None}"
        )
        if eeg_features:
            logger.debug(f"EEG: engagement={eeg_features.engagement_index:.2f}, quality={eeg_features.quality_score:.2f}")
        if eda_features:
            logger.debug(f"EDA: scl={eda_features.scl_mean:.2f}, scr_count={eda_features.scr_count_per_min:.1f}, quality={eda_features.quality_score:.2f}")
        logger.debug(
            f"Meters: EEG_focus={eeg_focus_meter:.2f}, "
            f"HRV_stress={hrv_stress_meter:.2f}, "
            f"EDA_arousal={eda_arousal_meter:.2f}"
        )
        
        # === Fuse into Focus & Stress scores ===
        focus_raw, stress_raw = self._fuse_scores(
            eeg_focus_meter,
            hrv_stress_meter,
            eda_arousal_meter,
            raw_features,
        )
        
        # === Smooth ===
        focus = self._focus_smoother.update(focus_raw)
        stress = self._stress_smoother.update(stress_raw)
        
        # Debug: log final scores
        logger.debug(f"Scores: focus_raw={focus_raw:.1f}%, focus={focus:.1f}%, stress={stress:.1f}%")
        
        # === Generate labels ===
        focus_label = self._categorize(focus)
        stress_label = self._categorize(stress)
        state_label = STATE_LABELS.get(
            (focus_label, stress_label),
            "Balanced / Mixed"
        )
        
        # Convert to 0-1 scale for StateScores
        scores = StateScores(
            focus=focus / 100,
            stress=stress / 100,
            relaxation=(100 - stress) / 100,  # Inverse of stress
        )
        
        return StateEstimate(
            timestamp=time.time(),
            scores=scores,
            label=state_label,
            explanation=None,
        )
    
    # =========================================================================
    # Feature extraction helpers
    # =========================================================================
    
    def _extract_eeg_features(self) -> Optional[EEGFeatures]:
        """Extract EEG features from buffer."""
        eeg_data = self._get_concatenated(self._eeg_buffer)
        if len(eeg_data) < 100:
            return None
        
        # Handle multi-channel: use first channel or average
        if eeg_data.ndim > 1:
            signal = eeg_data[:, 0]
        else:
            signal = eeg_data
        
        return compute_eeg_features(signal, self._eeg_rate)
    
    def _extract_eda_features(self) -> Optional[EDAFeatures]:
        """Extract EDA/GSR features from buffer."""
        gsr_data = self._get_concatenated(self._gsr_buffer)
        if len(gsr_data) < 50:
            return None
        return compute_eda_features(gsr_data, self._gsr_rate)
    
    def _extract_hrv_features(self) -> Optional[HRVFeatures]:
        """Extract HRV features from buffer."""
        ecg_data = self._get_concatenated(self._ecg_buffer)
        if len(ecg_data) < 250:
            return None
        return compute_hrv_features(ecg_data, self._ecg_rate)
    
    # =========================================================================
    # Modality meters (each 0-1)
    # =========================================================================
    
    def _compute_eeg_focus_meter(
        self,
        norm: NormalizedFeatures,
        features: Optional[EEGFeatures],
    ) -> float:
        """
        Compute EEG focus meter from normalized engagement index.
        
        High engagement index (above baseline) → high focus.
        High theta/alpha ratio → possible drowsiness → reduce focus.
        """
        if features is None or features.quality_score < 0.1:
            return 0.5  # Unknown
        
        # Map engagement z-score to meter
        # z=0 → 0.5, z=1 → 0.75, z=2 → ~0.9 (increased sensitivity)
        engagement_meter = 0.5 + 0.25 * np.tanh(norm.engagement_z / 1.5)
        
        # Penalize if theta/alpha is high (drowsy)
        if norm.theta_alpha_z > 1:
            engagement_meter *= 0.8
        
        return float(np.clip(engagement_meter, 0, 1))
    
    def _compute_hrv_stress_meter(
        self,
        norm: NormalizedFeatures,
        features: Optional[HRVFeatures],
    ) -> float:
        """
        Compute HRV stress meter from normalized RMSSD and HR.
        
        Low RMSSD (below baseline) → high stress.
        High HR (above baseline) → high stress.
        """
        if features is None or features.quality_score < 0.1:
            return 0.5  # Unknown
        
        # RMSSD: lower ratio = more stress
        # ratio=1 → 0.5, ratio=0.5 → 0.75, ratio=1.5 → 0.3
        rmssd_stress = 1 - (0.5 + 0.25 * np.tanh((norm.rmssd_ratio - 1) * 2))
        
        # HR: higher diff = more stress
        # 0 bpm diff → 0, +20 bpm → ~0.5, +40 bpm → ~0.8
        hr_stress = np.tanh(max(0, norm.hr_diff) / 30)
        
        # Combine
        meter = 0.7 * rmssd_stress + 0.3 * hr_stress
        return float(np.clip(meter, 0, 1))
    
    def _compute_eda_arousal_meter(
        self,
        norm: NormalizedFeatures,
        features: Optional[EDAFeatures],
    ) -> float:
        """
        Compute EDA arousal meter from normalized SCL and SCR count.
        
        High SCR count → high arousal.
        Rising SCL → high arousal.
        """
        if features is None or features.quality_score < 0.1:
            return 0.5  # Unknown
        
        # SCR count: higher z-score = more arousal (increased sensitivity)
        # z=0 → 0.5, z=1 → 0.7, z=2 → ~0.85
        scr_meter = 0.5 + 0.2 * np.tanh(norm.scr_count_z)
        
        # SCL: higher z-score = more arousal
        scl_meter = 0.5 + 0.2 * np.tanh(norm.scl_z)
        
        # Combine
        meter = 0.6 * scr_meter + 0.4 * scl_meter
        return float(np.clip(meter, 0, 1))
    
    # =========================================================================
    # Score fusion
    # =========================================================================
    
    def _fuse_scores(
        self,
        eeg_focus_meter: float,
        hrv_stress_meter: float,
        eda_arousal_meter: float,
        raw_features: Dict[str, float],
    ) -> tuple[float, float]:
        """
        Fuse modality meters into Focus (0-100) and Stress (0-100) scores.
        
        Focus: Primarily from EEG, adjusted by activity level.
        Stress: From EDA (primary) + HRV (secondary).
        """
        # === Focus Score ===
        # Base from EEG
        focus = eeg_focus_meter * 100
        
        # Adjust: if very relaxed (high RMSSD) and low EDA, slightly reduce focus
        # (user might be chilling rather than concentrating)
        if hrv_stress_meter < 0.3 and eda_arousal_meter < 0.3:
            focus *= 0.9
        
        # === Stress Score ===
        # EDA is primary arousal indicator
        # HRV provides physiological stress confirmation
        stress = (
            0.6 * eda_arousal_meter + 
            0.3 * hrv_stress_meter +
            0.1 * self._hr_diff_stress(raw_features)
        ) * 100
        
        return float(np.clip(focus, 0, 100)), float(np.clip(stress, 0, 100))
    
    def _hr_diff_stress(self, raw_features: Dict[str, float]) -> float:
        """Compute stress contribution from HR difference."""
        hr = raw_features.get("heart_rate", self._baseline.hrv.resting_hr_mean)
        hr_diff = hr - self._baseline.hrv.resting_hr_mean
        # Map 0-30 bpm diff to 0-1
        return float(np.clip(hr_diff / 30, 0, 1))
    
    def _categorize(self, score: float) -> str:
        """Categorize score into low/mid/high."""
        # Widened thresholds: 40/60 instead of 33/67 for more responsive labels
        if score < 40:
            return "low"
        elif score < 60:
            return "mid"
        else:
            return "high"
