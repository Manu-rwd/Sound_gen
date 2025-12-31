"""Tests for GSR serial client."""
from gsr_hub.acquisition.gsr_serial_client import GSRSerialClient, GSRSample


class FakeSerial:
    """Fake serial port for testing."""

    def __init__(self, lines: list[str]):
        self._lines = [line.encode() for line in lines]
        self._idx = 0
        self.timeout = 0.1
        self.is_open = True

    def readline(self) -> bytes:
        if self._idx >= len(self._lines):
            return b""
        line = self._lines[self._idx]
        self._idx += 1
        return line

    def reset_input_buffer(self) -> None:
        pass

    def close(self) -> None:
        self.is_open = False


def test_parse_line_ok():
    """Test parsing a valid GSR line."""
    client = GSRSerialClient(port="COM_FAKE")
    sample = client._parse_line("43534,GSR,2555\n")
    assert isinstance(sample, GSRSample)
    assert sample.value_raw == 2555
    assert sample.t_device_ms == 43534


def test_parse_line_wrong_label():
    """Test parsing a line with wrong sensor label."""
    client = GSRSerialClient(port="COM_FAKE")
    sample = client._parse_line("43534,FOO,2555\n")
    assert sample is None


def test_parse_line_malformed():
    """Test parsing malformed lines."""
    client = GSRSerialClient(port="COM_FAKE")

    # Too few parts
    assert client._parse_line("foo\n") is None
    # Non-numeric values
    assert client._parse_line("abc,GSR,def\n") is None
    # Empty line
    assert client._parse_line("\n") is None


def test_parse_line_custom_label():
    """Test parsing with custom sensor label."""
    client = GSRSerialClient(port="COM_FAKE", sensor_label="CUSTOM")
    sample = client._parse_line("1000,CUSTOM,1234\n")
    assert isinstance(sample, GSRSample)
    assert sample.value_raw == 1234


def test_read_samples_yields_only_valid(monkeypatch):
    """Test that read_samples only yields valid GSR samples."""
    fake = FakeSerial([
        "foo\n",
        "123,FOO,999\n",
        "43534,GSR,2555\n",
    ])

    def fake_serial(*args, **kwargs):
        return fake

    monkeypatch.setattr(
        "gsr_hub.acquisition.gsr_serial_client.serial.Serial",
        fake_serial
    )
    # Also patch sleep to speed up test
    monkeypatch.setattr(
        "gsr_hub.acquisition.gsr_serial_client.time.sleep",
        lambda x: None
    )

    client = GSRSerialClient(port="COM_FAKE")
    client.open()

    it = client.read_samples()
    s = next(it)
    assert s.value_raw == 2555
    assert s.t_device_ms == 43534


def test_read_samples_multiple(monkeypatch):
    """Test reading multiple valid samples."""
    fake = FakeSerial([
        "100,GSR,1000\n",
        "200,GSR,2000\n",
        "300,GSR,3000\n",
    ])

    def fake_serial(*args, **kwargs):
        return fake

    monkeypatch.setattr(
        "gsr_hub.acquisition.gsr_serial_client.serial.Serial",
        fake_serial
    )
    monkeypatch.setattr(
        "gsr_hub.acquisition.gsr_serial_client.time.sleep",
        lambda x: None
    )

    client = GSRSerialClient(port="COM_FAKE")
    client.open()

    samples = []
    it = client.read_samples()
    for _ in range(3):
        samples.append(next(it))

    assert len(samples) == 3
    assert samples[0].value_raw == 1000
    assert samples[1].value_raw == 2000
    assert samples[2].value_raw == 3000


def test_read_samples_without_open_raises():
    """Test that read_samples raises if port not opened."""
    client = GSRSerialClient(port="COM_FAKE")
    try:
        it = client.read_samples()
        next(it)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "not open" in str(e)
