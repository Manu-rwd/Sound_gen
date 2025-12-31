"""Tests for basic EEG feature extraction."""

import numpy as np
from sound_gen_hub.models import StreamMeta, SampleChunk
from sound_gen_hub.features.eeg_basic import compute_basic_eeg_features


def test_compute_basic_eeg_features():
    """Test basic feature computation."""
    # Create metadata
    meta = StreamMeta(
        name="Test-EEG",
        type="EEG",
        channel_count=2,
        nominal_srate=256.0
    )
    
    # Create chunk with known values
    timestamps = np.array([0.0, 0.5, 1.0])
    data = np.array([
        [1.0, 2.0, 3.0],  # Channel 0: mean=2.0, std=0.816...
        [2.0, 2.0, 2.0],  # Channel 1: mean=2.0, std=0.0
    ])
    
    chunk = SampleChunk(meta=meta, timestamps=timestamps, data=data)
    
    # Compute features
    fv = compute_basic_eeg_features(chunk)
    
    # Check timestamps
    assert fv.t_start == 0.0
    assert fv.t_end == 1.0
    
    # Check features
    assert "eeg_mean" in fv.features
    assert "eeg_std" in fv.features
    assert "eeg_abs_mean" in fv.features
    
    # Channel 0: [1, 2, 3]
    assert fv.features["eeg_mean"][0] == 2.0
    assert fv.features["eeg_abs_mean"][0] == 2.0
    assert fv.features["eeg_std"][0] > 0.8  # ~0.816
    
    # Channel 1: [2, 2, 2]
    assert fv.features["eeg_mean"][1] == 2.0
    assert fv.features["eeg_std"][1] == 0.0
    assert fv.features["eeg_abs_mean"][1] == 2.0


def test_compute_features_with_negative_values():
    """Test feature computation with negative values."""
    meta = StreamMeta(
        name="Test-EEG",
        type="EEG",
        channel_count=1,
        nominal_srate=256.0
    )
    
    timestamps = np.array([0.0, 1.0, 2.0])
    data = np.array([[-1.0, 0.0, 1.0]])  # mean=0, abs_mean=0.666...
    
    chunk = SampleChunk(meta=meta, timestamps=timestamps, data=data)
    fv = compute_basic_eeg_features(chunk)
    
    assert fv.features["eeg_mean"][0] == 0.0
    assert abs(fv.features["eeg_abs_mean"][0] - 2.0/3.0) < 0.01


def test_compute_features_multi_channel():
    """Test with multiple channels like real Muse (4 channels)."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    timestamps = np.arange(0, 10) / 256.0
    data = np.random.randn(4, 10)
    
    chunk = SampleChunk(meta=meta, timestamps=timestamps, data=data)
    fv = compute_basic_eeg_features(chunk)
    
    # Check all features have 4 values (one per channel)
    assert len(fv.features["eeg_mean"]) == 4
    assert len(fv.features["eeg_std"]) == 4
    assert len(fv.features["eeg_abs_mean"]) == 4
    
    # All features should be numeric
    for feat_name in ["eeg_mean", "eeg_std", "eeg_abs_mean"]:
        for val in fv.features[feat_name]:
            assert isinstance(val, (int, float))


def test_feature_vector_contains_stream_metadata():
    """Test that feature vector preserves stream metadata."""
    meta = StreamMeta(
        name="Muse-1AE4",
        type="EEG",  
        channel_count=4,
        nominal_srate=256.0,
        source_id="lsl-123"
    )
    
    timestamps = np.array([0.0, 1.0])
    data = np.random.randn(4, 2)
    
    chunk = SampleChunk(meta=meta, timestamps=timestamps, data=data)
    fv = compute_basic_eeg_features(chunk)
    
    # Check stream metadata is preserved
    assert fv.stream["name"] == "Muse-1AE4"
    assert fv.stream["type"] == "EEG"
    assert fv.stream["channel_count"] == 4
    assert fv.stream["nominal_srate"] == 256.0
    assert fv.stream["source_id"] == "lsl-123"
