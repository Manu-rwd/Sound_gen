"""Baseline profile and normalization for personalized state estimation.

Stores calibration-derived baselines and normalizes features to z-scores/ratios.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

EPSILON = 1e-10

# Default path for baseline storage
DEFAULT_BASELINE_PATH = Path(__file__).parent.parent.parent.parent / "data" / "baseline_profile.json"


@dataclass
class EEGBaseline:
    """EEG feature baselines from calibration."""
    engagement_mean: float = 1.0
    engagement_std: float = 0.5
    theta_alpha_mean: float = 1.0
    theta_alpha_std: float = 0.5
    alpha_power_mean: float = 10.0
    alpha_power_std: float = 5.0


@dataclass
class HRVBaseline:
    """HRV/ECG feature baselines from calibration."""
    resting_hr_mean: float = 70.0
    resting_hr_std: float = 10.0
    rmssd_mean: float = 40.0
    rmssd_std: float = 20.0
    sdnn_mean: float = 50.0
    sdnn_std: float = 25.0


@dataclass
class EDABaseline:
    """EDA/GSR feature baselines from calibration."""
    scl_mean: float = 2.0
    scl_std: float = 1.0
    scr_count_mean: float = 3.0  # SCRs per minute
    scr_count_std: float = 2.0


@dataclass
class BaselineProfile:
    """Complete baseline profile for personalized normalization.
    
    Contains calibration-derived mean and std for all feature types.
    Used to compute z-scores and ratios for normalized fusion.
    """
    
    # Modality baselines
    eeg: EEGBaseline = field(default_factory=EEGBaseline)
    hrv: HRVBaseline = field(default_factory=HRVBaseline)
    eda: EDABaseline = field(default_factory=EDABaseline)
    
    # Metadata
    user_id: Optional[str] = None
    calibration_date: Optional[str] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaselineProfile":
        """Create from dictionary."""
        return cls(
            eeg=EEGBaseline(**data.get("eeg", {})),
            hrv=HRVBaseline(**data.get("hrv", {})),
            eda=EDABaseline(**data.get("eda", {})),
            user_id=data.get("user_id"),
            calibration_date=data.get("calibration_date"),
            notes=data.get("notes"),
        )


def create_default_baseline() -> BaselineProfile:
    """Create a default baseline with population-typical values.
    
    Used when no calibration has been performed.
    These are approximate population averages.
    """
    return BaselineProfile(
        eeg=EEGBaseline(
            engagement_mean=1.0,
            engagement_std=0.5,
            theta_alpha_mean=1.0,
            theta_alpha_std=0.5,
            alpha_power_mean=10.0,
            alpha_power_std=5.0,
        ),
        hrv=HRVBaseline(
            resting_hr_mean=70.0,
            resting_hr_std=10.0,
            rmssd_mean=40.0,
            rmssd_std=20.0,
            sdnn_mean=50.0,
            sdnn_std=25.0,
        ),
        eda=EDABaseline(
            scl_mean=2.0,
            scl_std=1.0,
            scr_count_mean=3.0,
            scr_count_std=2.0,
        ),
        notes="Default baseline (no calibration)",
    )


def save_baseline(baseline: BaselineProfile, path: Optional[Path] = None) -> bool:
    """Save baseline profile to JSON file.
    
    Args:
        baseline: BaselineProfile to save
        path: File path (uses default if None)
        
    Returns:
        True if saved successfully
    """
    path = path or DEFAULT_BASELINE_PATH
    
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(baseline.to_dict(), f, indent=2)
        logger.info(f"Saved baseline profile to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save baseline: {e}")
        return False


def load_baseline(path: Optional[Path] = None) -> Optional[BaselineProfile]:
    """Load baseline profile from JSON file.
    
    Args:
        path: File path (uses default if None)
        
    Returns:
        BaselineProfile or None if not found/invalid
    """
    path = path or DEFAULT_BASELINE_PATH
    
    if not path.exists():
        logger.info(f"No baseline file at {path}")
        return None
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
        baseline = BaselineProfile.from_dict(data)
        logger.info(f"Loaded baseline profile from {path}")
        return baseline
    except Exception as e:
        logger.error(f"Failed to load baseline: {e}")
        return None


@dataclass
class NormalizedFeatures:
    """Normalized features for fusion (z-scores and ratios)."""
    
    # EEG normalized
    engagement_z: float = 0.0      # z-score of engagement index
    theta_alpha_z: float = 0.0     # z-score of theta/alpha ratio
    
    # HRV normalized
    hr_diff: float = 0.0           # HR - baseline HR (bpm)
    rmssd_ratio: float = 1.0       # RMSSD / baseline RMSSD
    rmssd_z: float = 0.0           # z-score of RMSSD
    
    # EDA normalized
    scl_diff: float = 0.0          # SCL - baseline SCL
    scl_z: float = 0.0             # z-score of SCL
    scr_count_z: float = 0.0       # z-score of SCR count


def normalize_features(
    raw_features: Dict[str, float],
    baseline: BaselineProfile,
) -> NormalizedFeatures:
    """
    Normalize raw features using baseline profile.
    
    Converts raw feature values to z-scores and ratios for
    fusion that is independent of individual differences.
    
    Args:
        raw_features: Dict with raw feature values:
            - engagement_index, theta_alpha_ratio (EEG)
            - heart_rate, rmssd (HRV)
            - scl_mean, scr_count_per_min (EDA)
        baseline: BaselineProfile with calibration data
        
    Returns:
        NormalizedFeatures ready for fusion
    """
    def z_score(value: float, mean: float, std: float) -> float:
        """Compute z-score with clamping."""
        if std < EPSILON:
            return 0.0
        z = (value - mean) / std
        return float(max(-3, min(3, z)))  # Clamp to ±3 std
    
    # EEG normalization
    engagement_z = z_score(
        raw_features.get("engagement_index", baseline.eeg.engagement_mean),
        baseline.eeg.engagement_mean,
        baseline.eeg.engagement_std,
    )
    
    theta_alpha_z = z_score(
        raw_features.get("theta_alpha_ratio", baseline.eeg.theta_alpha_mean),
        baseline.eeg.theta_alpha_mean,
        baseline.eeg.theta_alpha_std,
    )
    
    # HRV normalization
    hr = raw_features.get("heart_rate", baseline.hrv.resting_hr_mean)
    hr_diff = hr - baseline.hrv.resting_hr_mean
    
    rmssd = raw_features.get("rmssd", baseline.hrv.rmssd_mean)
    rmssd_ratio = rmssd / (baseline.hrv.rmssd_mean + EPSILON)
    rmssd_z = z_score(rmssd, baseline.hrv.rmssd_mean, baseline.hrv.rmssd_std)
    
    # EDA normalization
    scl = raw_features.get("scl_mean", baseline.eda.scl_mean)
    scl_diff = scl - baseline.eda.scl_mean
    scl_z = z_score(scl, baseline.eda.scl_mean, baseline.eda.scl_std)
    
    scr_count = raw_features.get("scr_count_per_min", baseline.eda.scr_count_mean)
    scr_count_z = z_score(scr_count, baseline.eda.scr_count_mean, baseline.eda.scr_count_std)
    
    return NormalizedFeatures(
        engagement_z=engagement_z,
        theta_alpha_z=theta_alpha_z,
        hr_diff=hr_diff,
        rmssd_ratio=rmssd_ratio,
        rmssd_z=rmssd_z,
        scl_diff=scl_diff,
        scl_z=scl_z,
        scr_count_z=scr_count_z,
    )
