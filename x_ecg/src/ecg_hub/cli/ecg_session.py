"""ECG session CLI."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

from ecg_hub.acquisition.ecg_serial_client import ECGSerialClient
from ecg_hub.acquisition.ecg_source import ECGSource
from ecg_hub.features.ecg_features import (
    compute_basic_ecg_features,
    summarize_status_flags,
)
from ecg_hub.interfaces import SensorSource, StreamInfo


def run_ecg_session(
    source: SensorSource,
    duration_sec: float,
    chunk_size: int,
    output_path: Path,
    backend_name: str,
    port: str,
) -> None:
    """
    Run an ECG session and log chunks to JSONL.

    Args:
        source: ECG source to read from
        duration_sec: Duration to run in seconds
        chunk_size: Number of samples per chunk
        output_path: Path to output JSONL file
        backend_name: Name of the backend (e.g., "ecg_serial")
        port: Serial port name
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source.connect()
    start_time = time.time()
    chunk_index = 0

    with open(output_path, "w") as f:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration_sec:
                break

            chunk = source.read_chunk(chunk_size)

            # Skip empty chunks
            if not chunk["values"]:
                continue

            # Compute features
            features = compute_basic_ecg_features(chunk["values"])
            status_summary = summarize_status_flags(chunk.get("status_flags"))

            # Build record
            record: Dict[str, Any] = {
                "backend": backend_name,
                "port": port,
                "chunk_index": chunk_index,
                "timestamp_start": chunk["timestamps"][0] if chunk["timestamps"] else 0.0,
                "timestamp_end": chunk["timestamps"][-1] if chunk["timestamps"] else 0.0,
                "sample_count": len(chunk["values"]),
                "features": features,
                "status_summary": status_summary,
            }

            # Write as JSONL
            f.write(json.dumps(record) + "\n")
            f.flush()

            chunk_index += 1

            # Print progress every 10 chunks
            if chunk_index % 10 == 0:
                print(f"  {chunk_index} chunks logged ({elapsed:.1f}s elapsed)")

    source.close()

    print(f"Session complete: {chunk_index} chunks logged")
    print(f"Duration: {time.time() - start_time:.1f}s")


def main() -> None:
    """Main entry point for ECG session CLI."""
    parser = argparse.ArgumentParser(
        description="Record ECG session from Teensy serial device"
    )
    parser.add_argument("--port", required=True, help="Serial port (e.g., COM15)")
    parser.add_argument(
        "--baudrate", type=int, default=115200, help="Baud rate (default: 115200)"
    )
    parser.add_argument(
        "--duration", type=float, required=True, help="Duration in seconds"
    )
    parser.add_argument(
        "--chunk-size", type=int, required=True, help="Samples per chunk"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Output JSONL file path"
    )

    args = parser.parse_args()

    # Create client and source
    client = ECGSerialClient(port_name=args.port, baudrate=args.baudrate)
    stream_info = StreamInfo(
        name="ECGSerial",
        sensor_type="ECG",
        channel_labels=["ECG"],
        sampling_rate_hz=None,  # Unknown, depends on Teensy sketch
    )
    source = ECGSource(client=client, stream_info=stream_info)

    output_path = Path(args.output)

    print(f"Starting ECG session on {args.port} for {args.duration} seconds...")
    print(f"Output: {output_path}")

    run_ecg_session(
        source=source,
        duration_sec=args.duration,
        chunk_size=args.chunk_size,
        output_path=output_path,
        backend_name="ecg_serial",
        port=args.port,
    )


if __name__ == "__main__":
    main()
