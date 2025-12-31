"""Tests for ECG serial client."""

from ecg_hub.acquisition.ecg_serial_client import ECGSample, ECGSerialClient


def test_import_ecg_serial_client():
    from ecg_hub.acquisition import ecg_serial_client  # noqa: F401


class FakeSerial:
    """Fake serial port for testing."""

    def __init__(self, lines):
        self._lines = [line.encode("ascii") for line in lines]
        self.index = 0

    def readline(self):
        if self.index >= len(self._lines):
            return b""
        line = self._lines[self.index]
        self.index += 1
        return line

    def close(self):
        pass


def test_parse_full_format(monkeypatch):
    """Test parsing full format: millis,ECG,value,status"""
    client = ECGSerialClient("COM_TEST")

    fake = FakeSerial(["12345,ECG,4028,OK\n"])
    monkeypatch.setattr(
        "ecg_hub.acquisition.ecg_serial_client.serial.Serial", lambda *a, **kw: fake
    )

    client.open()
    sample = client.read_sample()
    client.close()

    assert isinstance(sample, ECGSample)
    assert sample.timestamp_ms == 12345
    assert sample.value == 4028
    assert sample.status == "OK"


def test_parse_partial_format(monkeypatch):
    """Test parsing partial format: millis,ECG,value"""
    client = ECGSerialClient("COM_TEST")

    fake = FakeSerial(["12345,ECG,4028\n"])
    monkeypatch.setattr(
        "ecg_hub.acquisition.ecg_serial_client.serial.Serial", lambda *a, **kw: fake
    )

    client.open()
    sample = client.read_sample()
    client.close()

    assert isinstance(sample, ECGSample)
    assert sample.timestamp_ms == 12345
    assert sample.value == 4028
    assert sample.status is None


def test_parse_raw_value(monkeypatch):
    """Test parsing raw value format: value only"""
    client = ECGSerialClient("COM_TEST")

    fake = FakeSerial(["1999\n"])
    monkeypatch.setattr(
        "ecg_hub.acquisition.ecg_serial_client.serial.Serial", lambda *a, **kw: fake
    )

    client.open()
    sample = client.read_sample()
    client.close()

    assert sample is not None
    assert sample.timestamp_ms is None
    assert sample.value == 1999
    assert sample.status is None


def test_parse_loff_status(monkeypatch):
    """Test parsing LOFF status"""
    client = ECGSerialClient("COM_TEST")

    fake = FakeSerial(["42016,ECG,4028,LOFF\n"])
    monkeypatch.setattr(
        "ecg_hub.acquisition.ecg_serial_client.serial.Serial", lambda *a, **kw: fake
    )

    client.open()
    sample = client.read_sample()
    client.close()

    assert isinstance(sample, ECGSample)
    assert sample.timestamp_ms == 42016
    assert sample.value == 4028
    assert sample.status == "LOFF"


def test_parse_empty_line(monkeypatch):
    """Test parsing empty line returns None"""
    client = ECGSerialClient("COM_TEST")

    fake = FakeSerial(["\n"])
    monkeypatch.setattr(
        "ecg_hub.acquisition.ecg_serial_client.serial.Serial", lambda *a, **kw: fake
    )

    client.open()
    sample = client.read_sample()
    client.close()

    assert sample is None


def test_parse_malformed_line(monkeypatch):
    """Test parsing malformed line returns None"""
    client = ECGSerialClient("COM_TEST")

    fake = FakeSerial(["garbage,data,here\n"])
    monkeypatch.setattr(
        "ecg_hub.acquisition.ecg_serial_client.serial.Serial", lambda *a, **kw: fake
    )

    client.open()
    sample = client.read_sample()
    client.close()

    assert sample is None
