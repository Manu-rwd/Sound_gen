"""Integration tests for session hub with BrainFlow backend."""

import json
from pathlib import Path
from unittest.mock import MagicMock
from sound_gen_hub.cli import session_hub
from sound_gen_hub.acquisition.muse_brainflow import MuseBrainFlowSource
from sound_gen_hub.models import StreamMeta, SampleChunk
import numpy as np


class FakeMuseBrainFlowSource:
    """Fake BrainFlow source for integration testing."""
    
    def __init__(self, mac_address=None, buffer_size=None, client=None):
        self.mac_address = mac_address
        self.connected = False
        self.sample_num = 0
    
    def connect(self):
        """Fake connect."""
        self.connected = True
    
    def read_chunk(self, max_samples, timeout=1.0):
        """Return fake chunk."""
        if not self.connected:
            raise RuntimeError("Not connected")
        
        n_samples = min(max_samples, 10)
        data = np.random.randn(4, n_samples)
        timestamps = np.arange(
            self.sample_num,
            self.sample_num + n_samples
        ) * (1.0 / 256.0)
        self.sample_num += n_samples
        
        meta = StreamMeta(
            name="Muse-2-BrainFlow-Fake",
            type="EEG",
            channel_count=4,
            nominal_srate=256.0,
            source_id="fake-bf"
        )
        
        return SampleChunk(meta=meta, timestamps=timestamps, data=data)
    
    def close(self):
        """Fake close."""
        self.connected = False


def test_run_session_brainflow(tmp_path, monkeypatch):
    """Test running a full session with BrainFlow backend."""
    # Monkeypatch the create_source function to return our fake
    original_create_source = session_hub.create_source
    
    def fake_create_source(backend, name_filter, mac_address):
        if backend == "brainflow":
            return FakeMuseBrainFlowSource(mac_address=mac_address)
        else:
            return original_create_source(backend, name_filter, mac_address)
    
    monkeypatch.setattr(session_hub, "create_source", fake_create_source)
    
    # Run session
    output_path = tmp_path / "session_brainflow.jsonl"
    session_hub.run_session(
        backend="brainflow",
        duration_seconds=1.0,
        output_path=str(output_path),
        chunk_size=16,
        mac_address="00:11:22:33:44:55",
    )
    
    # Verify output file
    assert output_path.exists()
    
    content = output_path.read_text(encoding="utf-8").strip()
    lines = content.splitlines()
    
    assert len(lines) > 0, "Expected at least one logged chunk"
    
    # Verify entries
    entry = json.loads(lines[0])
    assert "t_start" in entry
    assert "t_end" in entry
    assert "stream" in entry
    assert "features" in entry
    
    # Check stream metadata
    assert entry["stream"]["type"] == "EEG"
    assert entry["stream"]["channel_count"] == 4
    
    # Check features exist
    assert "eeg_mean" in entry["features"]
    assert len(entry["features"]["eeg_mean"]) == 4
    
    # Check backend in extra
    assert entry["extra"]["backend"] == "brainflow"


def test_session_hub_create_source_lsl():
    """Test create_source with LSL backend."""
    source = session_hub.create_source(
        backend="lsl",
        name_filter="Test",
        mac_address=None
    )
    
    from sound_gen_hub.acquisition.muse_lsl import MuseLSLEEGSource
    assert isinstance(source, MuseLSLEEGSource)


def test_session_hub_create_source_brainflow():
    """Test create_source with BrainFlow backend."""
    source = session_hub.create_source(
        backend="brainflow",
        name_filter=None,
        mac_address="00:11:22:33:44:55"
    )
    
    from sound_gen_hub.acquisition.muse_brainflow import MuseBrainFlowSource
    assert isinstance(source, MuseBrainFlowSource)
    assert source._mac_address == "00:11:22:33:44:55"
