"""Integration tests for session hub with LSL backend."""

import json
import time
import threading
from pathlib import Path
from pylsl import StreamInfo, StreamOutlet
from sound_gen_hub.cli.session_hub import run_session


def test_run_session_lsl(tmp_path):
    """Test running a full session with LSL backend."""
    # Create synthetic Muse LSL stream
    info = StreamInfo(
        name="Muse-INT-TEST",
        type="EEG",
        channel_count=4,
        nominal_srate=256.0
    )
    
    outlet = StreamOutlet(info)
    stop_flag = threading.Event()
    
    def stream_data():
        """Push synthetic EEG data."""
        sample_num = 0
        while not stop_flag.is_set():
            sample = [float(sample_num * 0.001 + ch * 0.1) for ch in range(4)]
            outlet.push_sample(sample)
            sample_num += 1
            time.sleep(1.0 / 256.0)
    
    thread = threading.Thread(target=stream_data, daemon=True)
    thread.start()
    
    # Give stream time to start
    time.sleep(0.2)
    
    try:
        # Run session
        output_path = tmp_path / "session_lsl.jsonl"
        run_session(
            backend="lsl",
            duration_seconds=1.5,
            output_path=str(output_path),
            chunk_size=8,
            name_filter="Muse-INT-TEST",
        )
        
        # Verify output file
        assert output_path.exists()
        
        content = output_path.read_text(encoding="utf-8").strip()
        lines = content.splitlines()
        
        assert len(lines) > 0, "Expected at least one logged chunk"
        
        # Verify first entry
        entry = json.loads(lines[0])
        assert "t_start" in entry
        assert "t_end" in entry
        assert "stream" in entry
        assert "features" in entry
        assert "extra" in entry
        
        # Check stream metadata
        assert entry["stream"]["type"] == "EEG"
        assert "Muse" in entry["stream"]["name"]
        
        # Check features
        assert "eeg_mean" in entry["features"]
        assert "eeg_std" in entry["features"]
        assert "eeg_abs_mean" in entry["features"]
        
        # Check extra metadata
        assert entry["extra"]["backend"] == "lsl"
        
    finally:
        stop_flag.set()
        thread.join(timeout=1.0)
