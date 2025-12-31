"""ECG feature extraction."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


def compute_basic_ecg_features(values: List[float | int]) -> Dict[str, float]:
    """
    Compute basic descriptive statistics for ECG values.

    Args:
        values: List of ECG values

    Returns:
        Dict with mean, std, min, max
    """
    if not values:
        return {
            "mean": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }

    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "min": float(arr.min()),
        "max": float(arr.max()),
    }


def summarize_status_flags(status_flags: List[str] | None) -> Dict[str, int]:
    """
    Count occurrences of each status flag.

    Args:
        status_flags: List of status strings (e.g., "OK", "LOFF")

    Returns:
        Dict mapping each unique flag to its count
    """
    if not status_flags:
        return {}

    counts: Dict[str, int] = {}
    for flag in status_flags:
        if flag:  # Skip empty strings
            counts[flag] = counts.get(flag, 0) + 1
    return counts
