from __future__ import annotations
from typing import Sequence, Mapping, Any
import math
import statistics


def _basic_stats(values: Sequence[float]) -> dict[str, float]:
    """Compute basic statistics for a sequence of values."""
    if not values:
        return {
            "mean": math.nan,
            "std": math.nan,
            "min": math.nan,
            "max": math.nan,
        }

    if len(values) == 1:
        std = 0.0
    else:
        std = float(statistics.pstdev(values))

    return {
        "mean": float(statistics.fmean(values)),
        "std": std,
        "min": float(min(values)),
        "max": float(max(values)),
    }


def compute_gsr_features(samples: Sequence[Sequence[float]]) -> Mapping[str, Any]:
    """
    Compute simple summary features for a chunk of GSR samples.

    Args:
        samples: list of [gsr_raw] rows (n_samples x 1).

    Returns:
        Dict with gsr_mean, gsr_std, gsr_min, gsr_max.
    """
    if not samples:
        return {
            "gsr_mean": math.nan,
            "gsr_std": math.nan,
            "gsr_min": math.nan,
            "gsr_max": math.nan,
        }

    gsr_values = [row[0] for row in samples]
    stats = _basic_stats(gsr_values)

    return {
        "gsr_mean": stats["mean"],
        "gsr_std": stats["std"],
        "gsr_min": stats["min"],
        "gsr_max": stats["max"],
    }
