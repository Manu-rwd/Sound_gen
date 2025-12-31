"""Tests for GSRSource."""
from types import SimpleNamespace
import time

from gsr_hub.acquisition.gsr_source import GSRSource
from gsr_hub.acquisition import gsr_source


class FakeGSRSerialClient:
    """Fake GSRSerialClient for testing."""

    def __init__(self, *args, **kwargs):
        self.open_called = False
        self._values = [1000, 1001, 1002, 1003, 1004]

    def open(self):
        self.open_called = True

    def close(self):
        self.open_called = False

    def read_samples(self):
        """Yield simple objects with t_host & value_raw."""
        for v in self._values:
            yield SimpleNamespace(
                t_device_ms=0,
                t_host=time.time(),
                value_raw=v
            )


def test_gsr_source_stream_info():
    """Test that stream_info returns correct metadata."""
    src = GSRSource(port="COM_FAKE")
    info = src.stream_info

    assert info.name == "Teensy-GSR"
    assert info.type == "GSR"
    assert info.channel_count == 1
    assert info.nominal_srate == 50.0
    assert info.source_id == "gsr_serial"


def test_gsr_source_next_chunk(monkeypatch):
    """Test that next_chunk returns correct samples."""
    monkeypatch.setattr(gsr_source, "GSRSerialClient", FakeGSRSerialClient)

    src = GSRSource(port="COM_FAKE")
    src.connect()
    src.start()
    samples, t_start, t_end = src.next_chunk(3)

    assert len(samples) == 3
    assert samples[0][0] == 1000.0
    assert samples[1][0] == 1001.0
    assert samples[2][0] == 1002.0
    assert t_end >= t_start

    src.stop()
    src.close()


def test_gsr_source_full_lifecycle(monkeypatch):
    """Test the full connect/start/read/stop/close lifecycle."""
    monkeypatch.setattr(gsr_source, "GSRSerialClient", FakeGSRSerialClient)

    src = GSRSource(port="COM_FAKE")

    # Connect
    src.connect()

    # Start
    src.start()

    # Read some chunks
    samples1, _, _ = src.next_chunk(2)
    samples2, _, _ = src.next_chunk(2)

    assert len(samples1) == 2
    assert len(samples2) == 2
    assert samples1[0][0] == 1000.0
    assert samples2[0][0] == 1002.0

    # Stop
    src.stop()

    # Close
    src.close()


def test_gsr_source_next_chunk_without_start_raises(monkeypatch):
    """Test that next_chunk raises if start() not called."""
    monkeypatch.setattr(gsr_source, "GSRSerialClient", FakeGSRSerialClient)

    src = GSRSource(port="COM_FAKE")
    src.connect()

    try:
        src.next_chunk(1)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "start()" in str(e)

    src.close()
