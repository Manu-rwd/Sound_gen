"""GSR/EDA feature extraction for state estimation.

Computes tonic (SCL) and phasic (SCR) components for stress/arousal detection.
Enhanced with proper decomposition and normalized SCR count.
"""

from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


EPSILON = 1e-10  # Small value to avoid division by zero


@dataclass
class EDAFeatures:
    """Complete EDA/GSR feature set for state estimation."""
    
    # Tonic (Skin Conductance Level)
    scl_mean: float = 0.0          # Mean tonic level
    scl_std: float = 0.0           # Variability of tonic level
    scl_slope: float = 0.0         # Trend direction (linear regression slope)
    
    # Phasic (Skin Conductance Responses)
    scr_count: int = 0             # Number of SCRs detected
    scr_count_per_min: float = 0.0 # SCRs normalized to per-minute rate
    scr_mean_amplitude: float = 0.0 # Mean SCR amplitude
    scr_max_amplitude: float = 0.0  # Maximum SCR amplitude
    
    # Overall metrics
    total_range: float = 0.0       # Max - min of signal
    quality_score: float = 1.0     # Signal quality 0-1


@dataclass
class GSRFeatures:
    """Legacy GSR features (backward compatibility)."""
    mean_level: float = 0.0
    std: float = 0.0
    slope: float = 0.0
    scr_count: int = 0
    max_amplitude: float = 0.0


def compute_eda_features(
    signal: np.ndarray,
    sampling_rate: float = 50.0,
) -> EDAFeatures:
    """
    Compute complete EDA feature set with tonic/phasic decomposition.
    
    Args:
        signal: 1D array of EDA/GSR samples
        sampling_rate: Sampling rate in Hz
        
    Returns:
        EDAFeatures with tonic and phasic components
    """
    if len(signal) < 10:
        return EDAFeatures()
    
    signal = np.asarray(signal, dtype=float)
    window_seconds = len(signal) / sampling_rate
    
    # === Tonic (SCL) features ===
    scl_mean = float(np.mean(signal))
    scl_std = float(np.std(signal))
    
    # Compute slope via linear regression
    x = np.arange(len(signal))
    if len(signal) > 1:
        # Normalize x to seconds for interpretable slope
        x_seconds = x / sampling_rate
        coeffs = np.polyfit(x_seconds, signal, 1)
        scl_slope = float(coeffs[0])  # µS per second
    else:
        scl_slope = 0.0
    
    # === Phasic (SCR) features ===
    # High-pass filter: simple derivative to isolate phasic component
    if len(signal) > 1:
        phasic = np.diff(signal)
        phasic = np.insert(phasic, 0, 0)  # Pad to same length
    else:
        phasic = np.zeros_like(signal)
    
    # Detect SCRs: peaks in phasic component
    scr_peaks, scr_amplitudes = _detect_scrs(
        signal=signal,
        phasic=phasic,
        sampling_rate=sampling_rate,
        amplitude_threshold=0.01,  # 0.01 µS minimum
    )
    
    scr_count = len(scr_peaks)
    scr_count_per_min = (scr_count / window_seconds) * 60 if window_seconds > 0 else 0.0
    scr_mean_amplitude = float(np.mean(scr_amplitudes)) if scr_amplitudes else 0.0
    scr_max_amplitude = float(np.max(scr_amplitudes)) if scr_amplitudes else 0.0
    
    # Overall metrics
    total_range = float(np.max(signal) - np.min(signal))
    
    # Quality: low variance and flat signal might indicate disconnection
    quality_score = 1.0
    if scl_std < 0.001 and scl_mean < 0.1:
        quality_score = 0.2  # Likely disconnected
    elif scl_std < 0.01:
        quality_score = 0.6  # Low variability
    
    return EDAFeatures(
        scl_mean=scl_mean,
        scl_std=scl_std,
        scl_slope=scl_slope,
        scr_count=scr_count,
        scr_count_per_min=scr_count_per_min,
        scr_mean_amplitude=scr_mean_amplitude,
        scr_max_amplitude=scr_max_amplitude,
        total_range=total_range,
        quality_score=quality_score,
    )


def _detect_scrs(
    signal: np.ndarray,
    phasic: np.ndarray,
    sampling_rate: float,
    amplitude_threshold: float = 0.01,
    min_rise_time: float = 0.1,
    max_rise_time: float = 5.0,
) -> tuple[List[int], List[float]]:
    """
    Detect Skin Conductance Responses (SCRs) using derivative-based peak detection.
    
    Args:
        signal: Original EDA signal
        phasic: High-passed (derivative) version of signal
        sampling_rate: Sampling rate in Hz
        amplitude_threshold: Minimum SCR amplitude in µS
        min_rise_time: Minimum SCR rise time in seconds
        max_rise_time: Maximum SCR rise time in seconds
        
    Returns:
        Tuple of (peak_indices, peak_amplitudes)
    """
    if len(signal) < 10:
        return [], []
    
    min_samples = int(min_rise_time * sampling_rate)
    max_samples = int(max_rise_time * sampling_rate)
    
    peaks = []
    amplitudes = []
    
    # Find positive slope regions in phasic signal
    positive_slope = phasic > 0
    
    i = 0
    while i < len(signal) - min_samples:
        if positive_slope[i]:
            # Found start of potential SCR
            start_idx = i
            start_value = signal[i]
            
            # Find end of rise (where slope becomes negative or flat)
            j = i + 1
            while j < min(len(signal), i + max_samples) and positive_slope[j]:
                j += 1
            
            if j - i >= min_samples:
                # Valid rise time, check amplitude
                peak_idx = j
                peak_value = signal[min(peak_idx, len(signal) - 1)]
                amplitude = peak_value - start_value
                
                if amplitude >= amplitude_threshold:
                    peaks.append(peak_idx)
                    amplitudes.append(amplitude)
            
            i = j + int(0.5 * sampling_rate)  # Skip 0.5s after each detection
        else:
            i += 1
    
    return peaks, amplitudes


def compute_arousal_score(features: EDAFeatures) -> float:
    """
    Compute arousal/stress score from EDA features.
    
    Combines SCL deviation, SCR count, and slope for arousal indication.
    
    Returns:
        Arousal score 0-1
    """
    if features.quality_score < 0.3:
        return 0.5  # Uncertain
    
    # SCR frequency component (0-10 SCRs/min is typical range)
    scr_norm = min(features.scr_count_per_min / 10.0, 1.0)
    
    # SCL variability (coefficient of variation)
    if features.scl_mean > EPSILON:
        cv = features.scl_std / features.scl_mean
        cv_norm = min(cv * 5, 1.0)
    else:
        cv_norm = 0.0
    
    # Slope: rising SCL indicates increasing arousal
    slope_norm = float(np.clip(features.scl_slope * 10 + 0.5, 0, 1))
    
    # Combine with weights: SCR is primary indicator
    arousal = 0.5 * scr_norm + 0.3 * cv_norm + 0.2 * slope_norm
    return float(np.clip(arousal, 0, 1))


# ============================================================================
# Legacy functions for backward compatibility
# ============================================================================

def compute_gsr_features(
    signal: np.ndarray,
    sampling_rate: float = 50.0,
) -> GSRFeatures:
    """
    Compute GSR features (legacy interface).
    
    Args:
        signal: 1D array of GSR samples
        sampling_rate: Sampling rate in Hz
        
    Returns:
        GSRFeatures with basic metrics
    """
    eda = compute_eda_features(signal, sampling_rate)
    
    return GSRFeatures(
        mean_level=eda.scl_mean,
        std=eda.scl_std,
        slope=eda.scl_slope,
        scr_count=eda.scr_count,
        max_amplitude=eda.scr_max_amplitude,
    )


def compute_stress_from_gsr(features: GSRFeatures) -> float:
    """
    Estimate stress level from GSR features (legacy).
    
    Returns:
        Stress score 0-1
    """
    # Convert legacy features to EDA features for scoring
    eda = EDAFeatures(
        scl_mean=features.mean_level,
        scl_std=features.std,
        scl_slope=features.slope,
        scr_count=features.scr_count,
        scr_count_per_min=features.scr_count,  # Approximate
        scr_max_amplitude=features.max_amplitude,
    )
    return compute_arousal_score(eda)
