"""Tests for ECG features."""

from ecg_hub.features.ecg_features import (
    compute_basic_ecg_features,
    summarize_status_flags,
)


def test_import_ecg_features():
    from ecg_hub.features import ecg_features  # noqa: F401


def test_basic_ecg_features():
    """Test basic feature computation."""
    values = [1000, 1100, 1200]
    feats = compute_basic_ecg_features(values)
    assert feats["min"] == 1000
    assert feats["max"] == 1200
    assert feats["mean"] > 1090 and feats["mean"] < 1110
    assert feats["std"] > 0


def test_basic_ecg_features_empty():
    """Test feature computation with empty list."""
    values = []
    feats = compute_basic_ecg_features(values)
    assert str(feats["mean"]) == "nan"
    assert str(feats["std"]) == "nan"


def test_status_summary():
    """Test status flag counting."""
    flags = ["OK", "OK", "LOFF", "OK", "LOFF"]
    summary = summarize_status_flags(flags)
    assert summary["OK"] == 3
    assert summary["LOFF"] == 2


def test_status_summary_empty():
    """Test status flag counting with empty list."""
    summary = summarize_status_flags([])
    assert summary == {}


def test_status_summary_with_empty_strings():
    """Test status flag counting skips empty strings."""
    flags = ["OK", "", "OK", "", "LOFF"]
    summary = summarize_status_flags(flags)
    assert summary["OK"] == 2
    assert summary["LOFF"] == 1
    assert "" not in summary
