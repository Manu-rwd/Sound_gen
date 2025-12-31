"""GSR session runner CLI."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path

from gsr_hub.acquisition.gsr_source import GSRSource
from gsr_hub.features.gsr_features import compute_gsr_features


def run_gsr_session(
    port: str,
    duration: float,
    chunk_size: int,
    output_path: str,
) -> None:
    """
    Run a GSR recording session and log to JSONL.

    Args:
        port: Serial port (e.g., COM15)
        duration: Duration in seconds
        chunk_size: Samples per chunk
        output_path: Path for JSONL output file
    """
    source = GSRSource(port=port)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    source.connect()
    source.start()

    t_session_end = time.time() + duration
    chunk_idx = 0

    try:
        with out_file.open("w", encoding="utf-8") as f:
            while time.time() < t_session_end:
                samples, t_start, t_end = source.next_chunk(chunk_size)
                if not samples:
                    continue

                features = compute_gsr_features(samples)
                info = source.stream_info

                record = {
                    "t_start": t_start,
                    "t_end": t_end,
                    "stream": {
                        "name": info.name,
                        "type": info.type,
                        "channel_count": info.channel_count,
                        "nominal_srate": info.nominal_srate,
                        "source_id": info.source_id,
                    },
                    "features": features,
                    "now_playing": None,
                    "extra": {
                        "backend": "gsr_serial",
                        "port": port,
                        "chunk_index": chunk_idx,
                    },
                }
                f.write(json.dumps(record) + "\n")
                chunk_idx += 1
    finally:
        source.stop()
        source.close()


def main() -> None:
    """CLI entrypoint for GSR session recording."""
    parser = argparse.ArgumentParser(
        description="Run a GSR session from Teensy serial and log JSONL."
    )
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM15")
    parser.add_argument(
        "--duration", type=float, default=60.0, help="Seconds to record"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=64, help="Samples per chunk"
    )
    parser.add_argument(
        "--output",
        default="sessions/gsr_serial_session.jsonl",
        help="Output JSONL file path",
    )

    args = parser.parse_args()
    print(
        f"Starting GSR session on {args.port} for {args.duration} seconds...\n"
        f"Output: {args.output}"
    )

    run_gsr_session(
        port=args.port,
        duration=args.duration,
        chunk_size=args.chunk_size,
        output_path=args.output,
    )

    print("GSR session complete.")


if __name__ == "__main__":
    main()
