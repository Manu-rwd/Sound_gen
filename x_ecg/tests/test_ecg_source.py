"""Tests for ECG source."""

from ecg_hub.interfaces import SensorSource, StreamInfo


def test_import_ecg_source():
    from ecg_hub.acquisition import ecg_source  # noqa: F401


def test_stream_info_basic():
    info = StreamInfo(
        name="TestECG",
        sensor_type="ECG",
        channel_labels=["ECG"],
        sampling_rate_hz=250.0,
    )
    assert info.name == "TestECG"
    assert info.sensor_type == "ECG"
    assert info.channel_labels == ["ECG"]
    assert info.sampling_rate_hz == 250.0


def test_sensor_source_abc_contract():
    class Dummy(SensorSource):
        def connect(self) -> None:
            self.connected = True

        def read_chunk(self, max_samples: int):
            return {"timestamps": [], "values": []}

        def close(self) -> None:
            self.connected = False

    d = Dummy()
    d.connect()
    chunk = d.read_chunk(10)
    d.close()
    assert "timestamps" in chunk
    assert "values" in chunk


def test_ecg_source_chunk():
    """Test ECGSource with fake client."""
    from ecg_hub.acquisition.ecg_serial_client import ECGSample
    from ecg_hub.acquisition.ecg_source import ECGSource

    class FakeClient:
        def __init__(self, samples):
            self.samples = samples
            self.opened = False

        def open(self):
            self.opened = True

        def close(self):
            self.opened = False

        def read_sample(self):
            if not self.samples:
                return None
            return self.samples.pop(0)

    samples = [
        ECGSample(timestamp_ms=1000, value=2000, status="OK"),
        ECGSample(timestamp_ms=1004, value=2100, status="OK"),
        ECGSample(timestamp_ms=1008, value=2050, status="LOFF"),
    ]
    client = FakeClient(samples)
    info = StreamInfo(
        name="ECG",
        sensor_type="ECG",
        channel_labels=["ECG"],
        sampling_rate_hz=250.0,
    )

    source = ECGSource(client=client, stream_info=info)
    source.connect()
    chunk = source.read_chunk(max_samples=3)
    source.close()

    assert len(chunk["timestamps"]) == 3
    assert chunk["values"] == [2000, 2100, 2050]
    assert chunk["status_flags"] == ["OK", "OK", "LOFF"]
