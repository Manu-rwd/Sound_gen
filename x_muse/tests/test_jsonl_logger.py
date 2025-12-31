"""Tests for JSONL session logger."""

import json
from pathlib import Path
import pytest
from sound_gen_hub.logging.jsonl_logger import JSONLSessionLogger, SessionLogConfig
from sound_gen_hub.models import StreamMeta, FeatureVector


def test_jsonl_logger_basic_write(tmp_path):
    """Test basic JSONL writing."""
    output_file = tmp_path / "test.jsonl"
    
    config = SessionLogConfig(output_path=output_file, append=False)
    logger = JSONLSessionLogger(config)
    
    # Create a feature vector
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
        features={"mean": [1.0, 2.0, 3.0, 4.0]}
    )
    
    # Log it
    logger.open()
    logger.log_feature_vector(fv)
    logger.close()
    
    # Read back and verify
    assert output_file.exists()
    
    lines = output_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    
    entry = json.loads(lines[0])
    assert entry["t_start"] == 0.0
    assert entry["t_end"] == 1.0
    assert "stream" in entry
    assert entry["stream"]["name"] == "Muse-TEST"
    assert entry["features"]["mean"] == [1.0, 2.0, 3.0, 4.0]
    assert entry["now_playing"] is None
    assert entry["extra"] == {}


def test_jsonl_logger_multiple_entries(tmp_path):
    """Test logging multiple feature vectors."""
    output_file = tmp_path / "multi.jsonl"
    
    config = SessionLogConfig(output_path=output_file, append=False)
    logger = JSONLSessionLogger(config)
    
    meta = StreamMeta(name="Test", type="EEG", channel_count=2, nominal_srate=256.0)
    
    logger.open()
    
    for i in range(3):
        fv = FeatureVector.from_meta(
            meta=meta,
            t_start=float(i),
            t_end=float(i + 1),
            features={"value": i}
        )
        logger.log_feature_vector(fv)
    
    logger.close()
    
    # Verify
    lines = output_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    
    for i, line in enumerate(lines):
        entry = json.loads(line)
        assert entry["t_start"] == float(i)
        assert entry["features"]["value"] == i


def test_jsonl_logger_with_metadata(tmp_path):
    """Test logging with now_playing and extra metadata."""
    output_file = tmp_path / "meta.jsonl"
    
    config = SessionLogConfig(output_path=output_file, append=False)
    logger = JSONLSessionLogger(config)
    
    meta = StreamMeta(name="Test", type="EEG", channel_count=2, nominal_srate=256.0)
    fv = FeatureVector.from_meta(
        meta=meta,
        t_start=0.0,
        t_end=1.0,
        features={"test": 123}
    )
    
    logger.open()
    logger.log_feature_vector(
        fv,
        now_playing="Song Title - Artist",
        extra={"mood": "calm", "volume": 0.5}
    )
    logger.close()
    
    # Verify
    entry = json.loads(output_file.read_text(encoding="utf-8"))
    assert entry["now_playing"] == "Song Title - Artist"
    assert entry["extra"]["mood"] == "calm"
    assert entry["extra"]["volume"] == 0.5


def test_jsonl_logger_append_mode(tmp_path):
    """Test append mode."""
    output_file = tmp_path / "append.jsonl"
    
    meta = StreamMeta(name="Test", type="EEG", channel_count=2, nominal_srate=256.0)
    
    # First write
    config = SessionLogConfig(output_path=output_file, append=False)
    logger = JSONLSessionLogger(config)
    logger.open()
    
    fv1 = FeatureVector.from_meta(meta=meta, t_start=0.0, t_end=1.0, features={"a": 1})
    logger.log_feature_vector(fv1)
    logger.close()
    
    # Second write (append)
    config2 = SessionLogConfig(output_path=output_file, append=True)
    logger2 = JSONLSessionLogger(config2)
    logger2.open()
    
    fv2 = FeatureVector.from_meta(meta=meta, t_start=1.0, t_end=2.0, features={"a": 2})
    logger2.log_feature_vector(fv2)
    logger2.close()
    
    # Verify both entries exist
    lines = output_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    
    entry1 = json.loads(lines[0])
    entry2 = json.loads(lines[1])
    assert entry1["features"]["a"] == 1
    assert entry2["features"]["a"] == 2


def test_jsonl_logger_not_opened():
    """Test error when trying to log without opening."""
    config = SessionLogConfig(output_path=Path("/tmp/test.jsonl"))
    logger = JSONLSessionLogger(config)
    
    meta = StreamMeta(name="Test", type="EEG", channel_count=2, nominal_srate=256.0)
    fv = FeatureVector.from_meta(meta=meta, t_start=0.0, t_end=1.0, features={})
    
    with pytest.raises(RuntimeError, match="not opened"):
        logger.log_feature_vector(fv)


def test_jsonl_logger_creates_directories(tmp_path):
    """Test that logger creates parent directories."""
    output_file = tmp_path / "subdir" / "nested" / "test.jsonl"
    
    config = SessionLogConfig(output_path=output_file, append=False)
    logger = JSONLSessionLogger(config)
    
    meta = StreamMeta(name="Test", type="EEG", channel_count=2, nominal_srate=256.0)
    fv = FeatureVector.from_meta(meta=meta, t_start=0.0, t_end=1.0, features={})
    
    logger.open()
    logger.log_feature_vector(fv)
    logger.close()
    
    assert output_file.exists()
    assert output_file.parent.exists()
