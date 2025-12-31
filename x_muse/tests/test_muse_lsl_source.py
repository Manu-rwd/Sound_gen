"""Tests for Muse LSL EEG source."""

import time
import threading
import pytest
from pylsl import StreamInfo, StreamOutlet
from sound_gen_hub.acquisition.muse_lsl import MuseLSLEEGSource


@pytest.fixture
def muse_lsl_stream():
    """Create a synthetic Muse LSL EEG stream for testing."""
    # Create stream info that looks like a Muse device
    info = StreamInfo(
        name="Muse-TEST-EEG",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0,
        source_id="muse-test-123"
    )
    
    # Create outlet
    outlet = StreamOutlet(info)
    
    # Flag to control streaming thread
    stop_flag = threading.Event()
    
    def stream_data():
        """Push synthetic EEG data."""
        sample_num = 0
        while not stop_flag.is_set():
            # Generate synthetic sample (4 channels)
            sample = [float(sample_num * 0.001 + ch * 0.1) for ch in range(4)]
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


def test_muse_lsl_source_connect(muse_lsl_stream):
    """Test connecting to a Muse LSL stream."""
    source = MuseLSLEEGSource(name_filter="Muse-TEST")
    source.connect(wait_time=1.0)
    
    # Should not raise


def test_muse_lsl_source_connect_with_filter(muse_lsl_stream):
    """Test connecting with name filter."""
    source = MuseLSLEEGSource(name_filter="TEST")
    source.connect(wait_time=1.0)
    
    # Should find the stream


def test_muse_lsl_source_read_chunk(muse_lsl_stream):
    """Test reading chunks from Muse LSL stream."""
    source = MuseLSLEEGSource(name_filter="Muse-TEST")
    source.connect(wait_time=1.0)
    
    # Allow some samples to accumulate
    time.sleep(0.1)
    
    chunk = source.read_chunk(max_samples=8, timeout=1.0)
    
    assert chunk is not None
    assert chunk.data.shape[0] == 4  # 4 EEG channels
    assert chunk.data.shape[1] > 0  # At least some samples
    assert chunk.timestamps.shape[0] == chunk.data.shape[1]
    assert "Muse" in chunk.meta.name


def test_muse_lsl_source_not_connected():
    """Test that read_chunk raises when not connected."""
    source = MuseLSLEEGSource()
    
    with pytest.raises(RuntimeError, match="not connected"):
        source.read_chunk(max_samples=8)


def test_muse_lsl_source_no_stream_found():
    """Test connection failure when no Muse stream exists."""
    source = MuseLSLEEGSource(name_filter="NonExistent")
    
    # Should raise RuntimeError, either no streams found at all or filter doesn't match
    with pytest.raises(RuntimeError):
        source.connect(wait_time=0.5)


def test_muse_lsl_source_without_filter(muse_lsl_stream):
    """Test connecting without a name filter (should find any Muse stream)."""
    source = MuseLSLEEGSource()
    source.connect(wait_time=1.0)
    
    # Should connect to the Muse stream


def test_muse_lsl_source_multiple_reads(muse_lsl_stream):
    """Test reading multiple chunks sequentially."""
    source = MuseLSLEEGSource(name_filter="Muse-TEST")
    source.connect(wait_time=1.0)
    
    # Allow samples to accumulate
    time.sleep(0.2)
    
    # Read first chunk
    chunk1 = source.read_chunk(max_samples=16, timeout=1.0)
    assert chunk1 is not None
    
    # Allow more samples
    time.sleep(0.1)
    
    # Read second chunk
    chunk2 = source.read_chunk(max_samples=16, timeout=1.0)
    assert chunk2 is not None
    
    # Timestamps should be increasing
    if chunk1.timestamps.size > 0 and chunk2.timestamps.size > 0:
        assert chunk2.timestamps[0] > chunk1.timestamps[-1]
