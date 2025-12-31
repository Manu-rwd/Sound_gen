"""Smoke tests for CLI."""

import json
from pathlib import Path

from ecg_hub.cli.ecg_session import run_ecg_session
from ecg_hub.interfaces import SensorSource


def test_import_cli():
    from ecg_hub.cli import ecg_session  # noqa: F401


class FakeECGSource(SensorSource):
    """Fake ECG source for testing."""

    def __init__(self):
        self._calls = 0

    def connect(self) -> None:
        pass

    def read_chunk(self, max_samples: int):
        if self._calls > 1:
            return {"timestamps": [], "values": [], "status_flags": []}
        self._calls += 1
        return {
            "timestamps": [0.0, 0.01],
            "values": [2000, 2100],
            "status_flags": ["OK", "OK"],
        }

    def close(self) -> None:
        pass


def test_run_ecg_session_tmpdir(tmp_path: Path):
    """Test run_ecg_session with fake source."""
    out = tmp_path / "test_ecg.jsonl"
    source = FakeECGSource()
    run_ecg_session(
        source=source,
        duration_sec=0.1,
        chunk_size=2,
        output_path=out,
        backend_name="test_ecg",
        port="TEST",
    )
    assert out.exists()
    lines = out.read_text().strip().splitlines()
    assert len(lines) >= 1
    rec = json.loads(lines[0])
    assert rec["backend"] == "test_ecg"
    assert rec["sample_count"] == 2
    assert rec["port"] == "TEST"
    assert "features" in rec
    assert "status_summary" in rec
