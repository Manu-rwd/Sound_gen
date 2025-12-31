"""Tests for acquisition interfaces."""
from gsr_hub.acquisition.interfaces import StreamInfo, SensorSource


class DummySource:
    """Dummy implementation of SensorSource for testing."""

    def __init__(self) -> None:
        self._info = StreamInfo(
            name="dummy",
            type="DUMMY",
            channel_count=1,
            nominal_srate=1.0,
            source_id="dummy",
        )

    def connect(self) -> None:
        pass

    def start(self) -> None:
        pass

    def next_chunk(self, max_samples: int) -> tuple[list, float, float]:
        return [], 0.0, 0.0

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass

    @property
    def stream_info(self) -> StreamInfo:
        return self._info


def test_stream_info_basic():
    """Test that StreamInfo instantiates correctly with expected fields."""
    info = StreamInfo("n", "t", 1, 50.0, "src")
    assert info.name == "n"
    assert info.type == "t"
    assert info.channel_count == 1
    assert info.nominal_srate == 50.0
    assert info.source_id == "src"


def test_dummy_source_implements_interface():
    """Test that a dummy implementation of SensorSource can be used."""
    src: SensorSource = DummySource()
    src.connect()
    src.start()
    samples, t0, t1 = src.next_chunk(10)
    assert isinstance(samples, list)
    assert isinstance(t0, float)
    assert isinstance(t1, float)
    src.stop()
    src.close()


def test_stream_info_from_dummy_source():
    """Test that stream_info property returns correct StreamInfo."""
    src = DummySource()
    info = src.stream_info
    assert info.name == "dummy"
    assert info.type == "DUMMY"
    assert info.channel_count == 1
