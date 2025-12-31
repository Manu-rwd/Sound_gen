"""Tests for GSR feature extraction."""
import math
from gsr_hub.features.gsr_features import compute_gsr_features


def test_gsr_features_constant():
    """Test features for constant values."""
    samples = [[1000.0], [1000.0], [1000.0]]
    feats = compute_gsr_features(samples)

    assert feats["gsr_mean"] == 1000.0
    assert feats["gsr_std"] == 0.0
    assert feats["gsr_min"] == 1000.0
    assert feats["gsr_max"] == 1000.0


def test_gsr_features_two_values():
    """Test features for two different values."""
    samples = [[1000.0], [2000.0]]
    feats = compute_gsr_features(samples)

    assert feats["gsr_mean"] == 1500.0
    assert feats["gsr_min"] == 1000.0
    assert feats["gsr_max"] == 2000.0
    # population std for [1000, 2000]: sqrt((500^2 + 500^2) / 2) = 500
    assert feats["gsr_std"] == 500.0


def test_gsr_features_empty():
    """Test features for empty samples returns NaN."""
    feats = compute_gsr_features([])

    assert "gsr_mean" in feats
    assert "gsr_std" in feats
    assert "gsr_min" in feats
    assert "gsr_max" in feats
    assert math.isnan(feats["gsr_mean"])
    assert math.isnan(feats["gsr_std"])


def test_gsr_features_single_value():
    """Test features for single sample."""
    samples = [[42.0]]
    feats = compute_gsr_features(samples)

    assert feats["gsr_mean"] == 42.0
    assert feats["gsr_std"] == 0.0
    assert feats["gsr_min"] == 42.0
    assert feats["gsr_max"] == 42.0


def test_gsr_features_varying_values():
    """Test features for varying values."""
    samples = [[100.0], [200.0], [300.0], [400.0], [500.0]]
    feats = compute_gsr_features(samples)

    assert feats["gsr_mean"] == 300.0
    assert feats["gsr_min"] == 100.0
    assert feats["gsr_max"] == 500.0
    # Check std is positive and reasonable
    assert feats["gsr_std"] > 0
