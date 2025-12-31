"""Tests for LSL client utilities."""

import time
import threading
import numpy as np
import pytest
from pylsl import StreamInfo, StreamOutlet
from sound_gen_hub.acquisition.lsl_client import (
    discover_streams,
    select_streams_by_type,
    LSLStreamReader
)
from sound_gen_hub.models import StreamMeta


@pytest.fixture
def synthetic_eeg_stream():
    """Create a synthetic LSL EEG stream for testing."""
    # Create stream info
    info = StreamInfo(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0,
        source_id="test-synthetic-123"
    )
    
    # Create outlet
    outlet = StreamOutlet(info)
    
    # Flag to control streaming thread
    stop_flag = threading.Event()
    
    def stream_data():
        """Push synthetic data to the outlet."""
        sample_num = 0
        while not stop_flag.is_set():
            # Generate synthetic sample (4 channels)
            sample = [float(sample_num + ch) for ch in range(4)]
            outlet.push_sample(sample)
            sample_num += 1
            time.sleep(1.0 / 256.0)  # ~256 Hz
    
    # Start streaming thread
    thread = threading.Thread(target=stream_data, daemon=True)
    thread.start()
    
    # Give it a moment to start
    time.sleep(0.1)
    
    yield outlet
    
    # Cleanup
    stop_flag.set()
    thread.join(timeout=1.0)


def test_discover_streams(synthetic_eeg_stream):
    """Test discovering LSL streams."""
    streams = discover_streams(wait_time=1.0)
    
    assert len(streams) > 0
    assert any(s.name == "Muse-TEST" for s in streams)
    
    # Find our test stream
    test_stream = next(s for s in streams if s.name == "Muse-TEST")
    assert test_stream.type == "EEG"
    assert test_stream.channel_count == 4
    assert test_stream.nominal_srate == 256.0


def test_select_streams_by_type(synthetic_eeg_stream):
    """Test filtering streams by type."""
    all_streams = discover_streams(wait_time=1.0)
    eeg_streams = select_streams_by_type(all_streams, "EEG")
    
    assert len(eeg_streams) > 0
    assert all(s.type == "EEG" for s in eeg_streams)
    assert any(s.name == "Muse-TEST" for s in eeg_streams)


def test_lsl_stream_reader_connect(synthetic_eeg_stream):
    """Test LSLStreamReader connection."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    reader = LSLStreamReader(meta)
    reader.connect(wait_time=1.0)
    
    # Should not raise, connection successful


def test_lsl_stream_reader_pull_chunk(synthetic_eeg_stream):
    """Test pulling chunks from LSL stream."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    reader = LSLStreamReader(meta)
    reader.connect(wait_time=1.0)
    
    # Allow some samples to accumulate
    time.sleep(0.1)
    
    chunk = reader.pull_chunk(max_samples=16, timeout=1.0)
    
    assert chunk is not None
    assert chunk.data.shape[0] == 4  # 4 channels
    assert chunk.data.shape[1] > 0  # At least some samples
    assert chunk.timestamps.shape[0] == chunk.data.shape[1]
    assert chunk.meta.name == "Muse-TEST"


def test_lsl_stream_reader_not_connected():
    """Test that pull_chunk raises when not connected."""
    meta = StreamMeta(
        name="Muse-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    reader = LSLStreamReader(meta)
    
    with pytest.raises(RuntimeError, match="not connected"):
        reader.pull_chunk(max_samples=16)


def test_lsl_stream_reader_stream_not_found():
    """Test connection failure when stream doesn't exist."""
    meta = StreamMeta(
        name="NonExistent-Stream",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    reader = LSLStreamReader(meta)
    
    with pytest.raises(RuntimeError, match="Could not find LSL stream"):
        reader.connect(wait_time=0.5)
