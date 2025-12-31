"""Tests for core data models."""

import numpy as np
import pytest
from sound_gen_hub.models import StreamMeta, SampleChunk, FeatureVector


def test_stream_meta_creation():
    """Test StreamMeta creation and serialization."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0,
        source_id="test-123"
    )
    
    assert meta.name == "Muse-TEST"
    assert meta.type == "EEG"
    assert meta.channel_count == 4
    assert meta.nominal_srate == 256.0
    assert meta.source_id == "test-123"
    
    # Test dict conversion
    meta_dict = meta.to_dict()
    assert isinstance(meta_dict, dict)
    assert meta_dict["name"] == "Muse-TEST"
    assert meta_dict["channel_count"] == 4


def test_stream_meta_optional_source_id():
    """Test StreamMeta with optional source_id."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    assert meta.source_id is None


def test_sample_chunk_creation():
    """Test SampleChunk creation and validation."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    timestamps = np.array([0.0, 0.004, 0.008, 0.012])  # 4 samples
    data = np.random.randn(4, 4)  # 4 channels x 4 samples
    
    chunk = SampleChunk(meta=meta, timestamps=timestamps, data=data)
    
    assert chunk.meta.name == "Muse-TEST"
    assert chunk.timestamps.shape == (4,)
    assert chunk.data.shape == (4, 4)


def test_sample_chunk_shape_validation():
    """Test SampleChunk validates shapes correctly."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    # Wrong timestamps dimension
    with pytest.raises(ValueError, match="timestamps must be 1D"):
        SampleChunk(
            meta=meta,
            timestamps=np.array([[0.0, 0.004]]),
            data=np.random.randn(4, 2)
        )
    
    # Wrong data dimension
    with pytest.raises(ValueError, match="data must be 2D"):
        SampleChunk(
            meta=meta,
            timestamps=np.array([0.0, 0.004]),
            data=np.random.randn(4)
        )
    
    # Mismatched channel count
    with pytest.raises(ValueError, match="data channel count"):
        SampleChunk(
            meta=meta,
            timestamps=np.array([0.0, 0.004]),
            data=np.random.randn(3, 2)  # 3 channels but meta says 4
        )
    
    # Mismatched sample count
    with pytest.raises(ValueError, match="sample count"):
        SampleChunk(
            meta=meta,
            timestamps=np.array([0.0, 0.004, 0.008]),  # 3 samples
            data=np.random.randn(4, 2)  # 2 samples
        )


def test_feature_vector_creation():
    """Test FeatureVector creation and serialization."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    fv = FeatureVector.from_meta(
        meta=meta,
        t_start=0.0,
        t_end=1.0,
        features={
            "mean": [1.0, 2.0, 3.0, 4.0],
            "std": [0.5, 0.6, 0.7, 0.8]
        }
    )
    
    assert fv.t_start == 0.0
    assert fv.t_end == 1.0
    assert "mean" in fv.features
    assert "std" in fv.features
    assert fv.stream["name"] == "Muse-TEST"
    
    # Test Pydantic serialization
    fv_dict = fv.model_dump()
    assert isinstance(fv_dict, dict)
    assert "t_start" in fv_dict
    assert "t_end" in fv_dict
    assert "features" in fv_dict
    assert "stream" in fv_dict
    
    # Test JSON serialization
    fv_json = fv.model_dump_json()
    assert isinstance(fv_json, str)
    assert "t_start" in fv_json
    assert "Muse-TEST" in fv_json
