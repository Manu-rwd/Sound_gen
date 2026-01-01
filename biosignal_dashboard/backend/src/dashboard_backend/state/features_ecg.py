"""ECG feature extraction for state estimation.

Computes HRV metrics (RMSSD, SDNN) and heart rate for stress detection.
Enhanced with proper RR interval filtering and longer analysis windows.
"""

from __future__ import annotations
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass


EPSILON = 1e-10


@dataclass
class HRVFeatures:
    """Complete HRV feature set for state estimation."""
    
    # Basic metrics
    heart_rate: float = 0.0          # BPM from mean RR
    mean_rr: float = 0.0             # Mean RR interval in ms
    
    # Time-domain HRV
    rmssd: float = 0.0               # Root mean square of successive differences
    sdnn: float = 0.0                # Standard deviation of NN intervals
    pnn50: float = 0.0               # Percentage of successive RRs > 50ms
    
    # R-peak detection
    r_peak_count: int = 0            # Number of detected R-peaks
    valid_rr_count: int = 0          # Number of valid RR intervals
    
    # Quality metrics
    quality_score: float = 0.0       # Signal quality 0-1
    artifact_count: int = 0          # Number of rejected RR intervals


@dataclass
class ECGFeatures:
    """Legacy ECG features (backward compatibility)."""
    heart_rate: float = 0.0
    rmssd: float = 0.0
    sdnn: float = 0.0
    r_peak_count: int = 0
    quality: float = 0.0


def detect_r_peaks(
    signal: np.ndarray,
    sampling_rate: float = 250.0,
) -> List[int]:
    """
    Detect R-peaks using derivative-based approach with adaptive threshold.
    
    Args:
        signal: 1D array of ECG samples
        sampling_rate: Sampling rate in Hz
        
    Returns:
        List of R-peak indices
    """
    if len(signal) < 20:
        return []
    
    signal = np.asarray(signal, dtype=float)
    
    # Step 1: Bandpass effect via differentiation
    diff1 = np.diff(signal)
    diff2 = np.diff(diff1)
    
    # Step 2: Square to emphasize R-peaks
    if len(diff2) > 0:
        squared = diff1[:-1] ** 2
    else:
        return []
    
    # Step 3: Moving average smoothing
    window = int(0.08 * sampling_rate)  # 80ms window
    window = max(1, window)
    
    if len(squared) < window:
        return []
    
    kernel = np.ones(window) / window
    smoothed = np.convolve(squared, kernel, mode='same')
    
    # Step 4: Adaptive threshold
    threshold = np.mean(smoothed) + 0.5 * np.std(smoothed)
    
    # Step 5: Find peaks above threshold
    peaks = []
    min_distance = int(0.3 * sampling_rate)  # 300ms = 200 BPM max
    
    above_threshold = smoothed > threshold
    
    i = 0
    while i < len(above_threshold):
        if above_threshold[i]:
            # Find local maximum in this region
            start = i
            while i < len(above_threshold) and above_threshold[i]:
                i += 1
            end = i
            
            if end > start:
                local_max_idx = start + np.argmax(smoothed[start:end])
                peaks.append(local_max_idx)
                # Skip minimum distance
                i = local_max_idx + min_distance
        else:
            i += 1
    
    return peaks


def compute_rr_intervals(
    r_peaks: List[int],
    sampling_rate: float = 250.0,
    min_rr_ms: float = 300.0,
    max_rr_ms: float = 2000.0,
) -> Tuple[np.ndarray, int]:
    """
    Compute RR intervals from R-peak indices with filtering.
    
    Args:
        r_peaks: List of R-peak sample indices
        sampling_rate: Sampling rate in Hz
        min_rr_ms: Minimum valid RR interval in ms
        max_rr_ms: Maximum valid RR interval in ms
        
    Returns:
        Tuple of (valid_rr_intervals_ms, artifact_count)
    """
    if len(r_peaks) < 2:
        return np.array([]), 0
    
    # Compute RR intervals in milliseconds
    rr_samples = np.diff(r_peaks)
    rr_ms = (rr_samples / sampling_rate) * 1000
    
    # Filter valid RR intervals
    valid_mask = (rr_ms >= min_rr_ms) & (rr_ms <= max_rr_ms)
    valid_rr = rr_ms[valid_mask]
    artifact_count = int(np.sum(~valid_mask))
    
    return valid_rr, artifact_count


def compute_hrv_features(
    signal: np.ndarray,
    sampling_rate: float = 250.0,
) -> HRVFeatures:
    """
    Compute complete HRV feature set from raw ECG.
    
    Uses a window of 60s+ for reliable HRV metrics.
    
    Args:
        signal: 1D array of ECG samples
        sampling_rate: Sampling rate in Hz
        
    Returns:
        HRVFeatures with HR and HRV metrics
    """
    if len(signal) < 50:
        return HRVFeatures()
    
    # Detect R-peaks
    r_peaks = detect_r_peaks(signal, sampling_rate)
    
    if len(r_peaks) < 2:
        return HRVFeatures(r_peak_count=len(r_peaks), quality_score=0.1)
    
    # Compute RR intervals
    rr_intervals, artifact_count = compute_rr_intervals(r_peaks, sampling_rate)
    
    if len(rr_intervals) < 2:
        return HRVFeatures(
            r_peak_count=len(r_peaks),
            artifact_count=artifact_count,
            quality_score=0.2,
        )
    
    # === Time-domain HRV metrics ===
    
    # Mean RR and Heart Rate
    mean_rr = float(np.mean(rr_intervals))
    heart_rate = 60000 / mean_rr if mean_rr > 0 else 0.0
    
    # SDNN: Standard deviation of NN intervals
    sdnn = float(np.std(rr_intervals))
    
    # RMSSD: Root mean square of successive differences
    rr_diffs = np.diff(rr_intervals)
    if len(rr_diffs) > 0:
        rmssd = float(np.sqrt(np.mean(rr_diffs ** 2)))
    else:
        rmssd = 0.0
    
    # pNN50: Percentage of successive RR differences > 50ms
    if len(rr_diffs) > 0:
        pnn50 = float(np.mean(np.abs(rr_diffs) > 50) * 100)
    else:
        pnn50 = 0.0
    
    # Quality score based on detection success
    valid_rr_count = len(rr_intervals)
    total_possible = len(r_peaks) - 1 if len(r_peaks) > 1 else 1
    quality_score = valid_rr_count / total_possible if total_possible > 0 else 0.0
    quality_score = min(quality_score, 1.0)
    
    # Boost quality if we have enough data
    if valid_rr_count >= 10:
        quality_score = max(quality_score, 0.7)
    
    return HRVFeatures(
        heart_rate=heart_rate,
        mean_rr=mean_rr,
        rmssd=rmssd,
        sdnn=sdnn,
        pnn50=pnn50,
        r_peak_count=len(r_peaks),
        valid_rr_count=valid_rr_count,
        quality_score=quality_score,
        artifact_count=artifact_count,
    )


def compute_hrv_stress_score(features: HRVFeatures) -> float:
    """
    Compute stress score from HRV features.
    
    Lower HRV (RMSSD) and higher HR indicate higher stress.
    
    Returns:
        Stress score 0-1
    """
    if features.quality_score < 0.3:
        return 0.5  # Uncertain
    
    # HR component: higher HR = more stress
    # Normal resting range 60-100 BPM
    hr_norm = (features.heart_rate - 60) / 40  # 0 at 60, 1 at 100 BPM
    hr_stress = float(np.clip(hr_norm, 0, 1))
    
    # RMSSD component: lower RMSSD = more stress
    # Normal RMSSD is 20-80ms (healthy adults)
    rmssd_norm = (features.rmssd - 20) / 60  # 0 at 20ms, 1 at 80ms
    rmssd_relaxation = float(np.clip(rmssd_norm, 0, 1))
    rmssd_stress = 1 - rmssd_relaxation
    
    # Combine with weights: RMSSD is primary HRV indicator
    stress = 0.3 * hr_stress + 0.7 * rmssd_stress
    return float(np.clip(stress, 0, 1))


# ============================================================================
# Legacy functions for backward compatibility
# ============================================================================

def compute_ecg_features(
    signal: np.ndarray,
    sampling_rate: float = 250.0,
) -> ECGFeatures:
    """
    Compute ECG features (legacy interface).
    
    Args:
        signal: 1D array of ECG samples
        sampling_rate: Sampling rate in Hz
        
    Returns:
        ECGFeatures with basic metrics
    """
    hrv = compute_hrv_features(signal, sampling_rate)
    
    return ECGFeatures(
        heart_rate=hrv.heart_rate,
        rmssd=hrv.rmssd,
        sdnn=hrv.sdnn,
        r_peak_count=hrv.r_peak_count,
        quality=hrv.quality_score,
    )


def compute_stress_from_ecg(features: ECGFeatures) -> float:
    """
    Estimate stress level from ECG features (legacy).
    
    Returns:
        Stress score 0-1
    """
    hrv = HRVFeatures(
        heart_rate=features.heart_rate,
        rmssd=features.rmssd,
        sdnn=features.sdnn,
        r_peak_count=features.r_peak_count,
        quality_score=features.quality,
    )
    return compute_hrv_stress_score(hrv)
