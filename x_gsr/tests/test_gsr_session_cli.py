"""Tests for GSR session CLI."""
from pathlib import Path
import json
import tempfile
import time

from gsr_hub.cli.gsr_session import run_gsr_session


class FakeGSRSource:
    """Fake GSRSource for testing the CLI."""

    def __init__(self, port: str):
        self.port = port
        self._call_count = 0
        self._info = type(
            "Info",
            (),
            {
                "name": "Fake-GSR",
                "type": "GSR",
                "channel_count": 1,
                "nominal_srate": 50.0,
                "source_id": "fake",
            },
        )()

    @property
    def stream_info(self):
        return self._info

    def connect(self):
        pass

    def start(self):
        pass

    def next_chunk(self, max_samples: int):
        # After a few chunks, return empty to shorten the test
        self._call_count += 1
        if self._call_count > 3:
            return [], time.time(), time.time()
        samples = [[1000.0] for _ in range(max_samples)]
        t = time.time()
        return samples, t, t + 0.01

    def stop(self):
        pass

    def close(self):
        pass


def test_run_gsr_session_writes_jsonl(monkeypatch):
    """Test that run_gsr_session creates a valid JSONL file."""
    monkeypatch.setattr(
        "gsr_hub.cli.gsr_session.GSRSource",
        lambda port: FakeGSRSource(port),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "gsr.jsonl"
        run_gsr_session(
            port="COM_FAKE",
            duration=0.5,
            chunk_size=4,
            output_path=str(out_path),
        )

        assert out_path.exists()
        lines = out_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) > 0

        first = json.loads(lines[0])
        assert first["stream"]["type"] == "GSR"
        assert "gsr_mean" in first["features"]


def test_run_gsr_session_jsonl_structure(monkeypatch):
    """Test the structure of JSONL records."""
    monkeypatch.setattr(
        "gsr_hub.cli.gsr_session.GSRSource",
        lambda port: FakeGSRSource(port),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "gsr.jsonl"
        run_gsr_session(
            port="COM_TEST",
            duration=0.5,
            chunk_size=8,
            output_path=str(out_path),
        )

        lines = out_path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])

        # Check top-level keys
        assert "t_start" in first
        assert "t_end" in first
        assert "stream" in first
        assert "features" in first
        assert "now_playing" in first
        assert "extra" in first

        # Check stream structure
        stream = first["stream"]
        assert stream["name"] == "Fake-GSR"
        assert stream["type"] == "GSR"
        assert stream["channel_count"] == 1

        # Check features structure
        features = first["features"]
        assert "gsr_mean" in features
        assert "gsr_std" in features
        assert "gsr_min" in features
        assert "gsr_max" in features

        # Check extra structure
        extra = first["extra"]
        assert extra["backend"] == "gsr_serial"
        assert extra["port"] == "COM_TEST"
        assert "chunk_index" in extra


def test_run_gsr_session_creates_parent_dirs(monkeypatch):
    """Test that parent directories are created if needed."""
    monkeypatch.setattr(
        "gsr_hub.cli.gsr_session.GSRSource",
        lambda port: FakeGSRSource(port),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "nested" / "dir" / "gsr.jsonl"
        run_gsr_session(
            port="COM_FAKE",
            duration=0.3,
            chunk_size=4,
            output_path=str(out_path),
        )

        assert out_path.exists()
        assert out_path.parent.exists()
