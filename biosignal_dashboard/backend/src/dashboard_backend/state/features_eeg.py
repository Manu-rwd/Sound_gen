"""EEG feature extraction for state estimation.

Computes band power features using FFT for focus/relaxation scoring.
Enhanced with Engagement Index, Theta/Alpha ratio, and optional FAA.
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field


EPSILON = 1e-10  # Small value to avoid division by zero


@dataclass
class EEGBandPowers:
    """EEG frequency band powers in µV²."""
    delta: float = 0.0   # 0.5-4 Hz (deep sleep)
    theta: float = 0.0   # 4-7 Hz (drowsiness, meditation)
    alpha: float = 0.0   # 8-12 Hz (relaxed, eyes closed)
    beta: float = 0.0    # 13-30 Hz (active thinking, focus)
    gamma: float = 0.0   # 30-50 Hz (high-level processing)
    
    @property
    def total(self) -> float:
        return self.delta + self.theta + self.alpha + self.beta + self.gamma
    
    def normalized(self) -> Dict[str, float]:
        """Return band powers as proportions of total power."""
        t = self.total
        if t == 0:
            return {"delta": 0, "theta": 0, "alpha": 0, "beta": 0, "gamma": 0}
        return {
            "delta": self.delta / t,
            "theta": self.theta / t,
            "alpha": self.alpha / t,
            "beta": self.beta / t,
            "gamma": self.gamma / t,
        }


@dataclass
class EEGFeatures:
    """Complete EEG feature set for state estimation."""
    
    # Band powers
    band_powers: EEGBandPowers = field(default_factory=EEGBandPowers)
    
    # Derived metrics
    engagement_index: float = 0.0      # beta / (alpha + theta + ε)
    theta_alpha_ratio: float = 0.0     # theta / (alpha + ε) - drowsiness
    alpha_beta_ratio: float = 0.0      # alpha / (alpha + beta) - relaxation
    
    # Frontal Alpha Asymmetry (optional, requires left/right channels)
    frontal_alpha_asymmetry: Optional[float] = None
    
    # Quality metrics
    total_power: float = 0.0
    artifact_ratio: float = 0.0  # Proportion of samples marked as artifacts
    quality_score: float = 1.0   # Overall signal quality 0-1


def compute_band_powers(
    signal: np.ndarray,
    sampling_rate: float = 256.0,
) -> EEGBandPowers:
    """
    Compute EEG band powers using FFT.
    
    Args:
        signal: 1D array of EEG samples (single channel)
        sampling_rate: Sampling rate in Hz
        
    Returns:
        EEGBandPowers with power in each frequency band
    """
    if len(signal) < 4:
        return EEGBandPowers()
    
    # Apply Hanning window to reduce spectral leakage
    windowed = signal * np.hanning(len(signal))
    
    # Compute FFT
    fft = np.fft.rfft(windowed)
    power = np.abs(fft) ** 2
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sampling_rate)
    
    # Compute power in each band (using blueprint definitions)
    def band_power(low: float, high: float) -> float:
        mask = (freqs >= low) & (freqs < high)
        return float(np.sum(power[mask]))
    
    return EEGBandPowers(
        delta=band_power(0.5, 4),
        theta=band_power(4, 7),
        alpha=band_power(8, 12),
        beta=band_power(13, 30),
        gamma=band_power(30, 50),
    )


def compute_engagement_index(band_powers: EEGBandPowers) -> float:
    """
    Compute Engagement Index: beta / (alpha + theta + ε).
    
    Higher values indicate greater cognitive engagement.
    Used as primary focus indicator.
    
    Returns:
        Engagement index (raw ratio, typically 0.5-3.0)
    """
    denom = band_powers.alpha + band_powers.theta + EPSILON
    return band_powers.beta / denom


def compute_theta_alpha_ratio(band_powers: EEGBandPowers) -> float:
    """
    Compute Theta/Alpha ratio: theta / (alpha + ε).
    
    Higher values indicate drowsiness or meditative state.
    Low values indicate alertness.
    
    Returns:
        Theta/Alpha ratio (typically 0.3-2.0)
    """
    return band_powers.theta / (band_powers.alpha + EPSILON)


def compute_alpha_beta_ratio(band_powers: EEGBandPowers) -> float:
    """
    Compute Alpha/(Alpha+Beta) ratio for relaxation.
    
    Higher values indicate relaxation, lower values indicate active thinking.
    
    Returns:
        Relaxation ratio 0-1
    """
    denom = band_powers.alpha + band_powers.beta
    if denom < EPSILON:
        return 0.5
    return band_powers.alpha / denom


def compute_frontal_alpha_asymmetry(
    alpha_left: float,
    alpha_right: float,
) -> float:
    """
    Compute Frontal Alpha Asymmetry (FAA).
    
    FAA = log(alpha_right) - log(alpha_left)
    
    Positive values: greater right frontal alpha = approach motivation
    Negative values: greater left frontal alpha = withdrawal motivation
    
    For Muse: AF7 (left) and AF8 (right) electrodes.
    
    Args:
        alpha_left: Alpha power from left frontal electrode
        alpha_right: Alpha power from right frontal electrode
        
    Returns:
        FAA score (typically -1 to +1)
    """
    # Add epsilon to avoid log(0)
    left = alpha_left + EPSILON
    right = alpha_right + EPSILON
    return float(np.log(right) - np.log(left))


def compute_eeg_features(
    signal: np.ndarray,
    sampling_rate: float = 256.0,
    left_channel: Optional[np.ndarray] = None,
    right_channel: Optional[np.ndarray] = None,
) -> EEGFeatures:
    """
    Compute complete EEG feature set.
    
    Args:
        signal: 1D array of EEG samples (single channel or average)
        sampling_rate: Sampling rate in Hz
        left_channel: Optional left frontal channel for FAA (e.g., AF7)
        right_channel: Optional right frontal channel for FAA (e.g., AF8)
        
    Returns:
        EEGFeatures with all derived metrics
    """
    band_powers = compute_band_powers(signal, sampling_rate)
    
    # Compute derived metrics
    engagement_index = compute_engagement_index(band_powers)
    theta_alpha_ratio = compute_theta_alpha_ratio(band_powers)
    alpha_beta_ratio = compute_alpha_beta_ratio(band_powers)
    
    # Compute FAA if both channels provided
    faa = None
    if left_channel is not None and right_channel is not None:
        left_powers = compute_band_powers(left_channel, sampling_rate)
        right_powers = compute_band_powers(right_channel, sampling_rate)
        faa = compute_frontal_alpha_asymmetry(left_powers.alpha, right_powers.alpha)
    
    # Estimate artifact ratio (high amplitude = artifact)
    # Note: Muse EEG shows ±1000µV normally, so threshold must be higher
    artifact_threshold = 2000.0  # µV threshold (was 100, raised for Muse)
    if len(signal) > 0:
        artifact_ratio = float(np.mean(np.abs(signal) > artifact_threshold))
    else:
        artifact_ratio = 0.0
    
    # Quality score based on artifacts and total power
    quality_score = max(0.0, 1.0 - artifact_ratio)
    
    return EEGFeatures(
        band_powers=band_powers,
        engagement_index=engagement_index,
        theta_alpha_ratio=theta_alpha_ratio,
        alpha_beta_ratio=alpha_beta_ratio,
        frontal_alpha_asymmetry=faa,
        total_power=band_powers.total,
        artifact_ratio=artifact_ratio,
        quality_score=quality_score,
    )


# ============================================================================
# Legacy functions for backward compatibility with current StateEstimator
# ============================================================================

def compute_focus_score(band_powers: EEGBandPowers) -> float:
    """
    Compute focus score from EEG band powers (legacy).
    
    Uses engagement index normalized to 0-1.
    
    Returns:
        Focus score 0-1
    """
    engagement = compute_engagement_index(band_powers)
    # Sigmoid-like normalization: engagement of 1.0 → 0.5, 2.0 → 0.67
    score = engagement / (1 + engagement)
    return float(np.clip(score, 0, 1))


def compute_relaxation_score(band_powers: EEGBandPowers) -> float:
    """
    Compute relaxation score from EEG band powers (legacy).
    
    Uses alpha/(alpha+beta) ratio.
    
    Returns:
        Relaxation score 0-1
    """
    return float(np.clip(compute_alpha_beta_ratio(band_powers), 0, 1))
