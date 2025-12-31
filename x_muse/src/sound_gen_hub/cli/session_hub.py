"""Session hub CLI for orchestrating EEG acquisition and logging."""

import time
import argparse
from pathlib import Path
from typing import Literal

from ..acquisition.muse_lsl import MuseLSLEEGSource
from ..acquisition.muse_brainflow import MuseBrainFlowSource
from ..acquisition.base import EEGSource
from ..features.eeg_basic import compute_basic_eeg_features
from ..logging.jsonl_logger import JSONLSessionLogger, SessionLogConfig

BackendType = Literal["lsl", "brainflow"]


def create_source(
    backend: BackendType,
    name_filter: str | None,
    mac_address: str | None,
) -> EEGSource:
    """
    Create an EEG source based on backend type.
    
    Args:
        backend: "lsl" or "brainflow"
        name_filter: Optional filter for LSL stream names
        mac_address: Optional MAC address for BrainFlow
        
    Returns:
        EEGSource instance
        
    Raises:
        ValueError: If backend type is unknown
    """
    if backend == "lsl":
        return MuseLSLEEGSource(name_filter=name_filter)
    elif backend == "brainflow":
        return MuseBrainFlowSource(mac_address=mac_address)
    else:
        raise ValueError(f"Unknown backend: {backend}")


def run_session(
    backend: BackendType,
    duration_seconds: float,
    output_path: str,
    chunk_size: int = 64,
    name_filter: str | None = None,
    mac_address: str | None = None,
) -> None:
    """
    Run an EEG acquisition session.
    
    Args:
        backend: "lsl" or "brainflow"
        duration_seconds: Session duration in seconds
        output_path: Path to output JSONL file
        chunk_size: Maximum samples per chunk
        name_filter: Optional LSL stream name filter
        mac_address: Optional BrainFlow MAC address
    """
    print(f"Starting {backend} session for {duration_seconds:.1f} seconds...")
    print(f"Output: {output_path}")
    
    # Create source and logger
    source = create_source(backend, name_filter=name_filter, mac_address=mac_address)
    logger = JSONLSessionLogger(SessionLogConfig(output_path=Path(output_path), append=False))

    # Connect
    print("Connecting to EEG stream...")
    source.connect()
    logger.open()

    start = time.time()
    chunk_count = 0
    
    try:
        while time.time() - start < duration_seconds:
            chunk = source.read_chunk(max_samples=chunk_size, timeout=1.0)
            
            if chunk is None:
                continue

            # Compute features
            fv = compute_basic_eeg_features(chunk)
            
            # Log with backend info
            logger.log_feature_vector(
                fv,
                now_playing=None,  # Hook for future integration
                extra={"backend": backend}
            )
            
            chunk_count += 1
            
            if chunk_count % 10 == 0:
                elapsed = time.time() - start
                print(f"  {chunk_count} chunks logged ({elapsed:.1f}s elapsed)")
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        logger.close()
        if hasattr(source, "close"):
            source.close()
        
        elapsed = time.time() - start
        print(f"\nSession complete: {chunk_count} chunks logged to {output_path}")
        print(f"Duration: {elapsed:.1f}s")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="EEG session hub for Muse 2",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--backend",
        choices=["lsl", "brainflow"],
        default="lsl",
        help="EEG backend to use"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Session duration in seconds"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to output JSONL log file"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=64,
        help="Maximum samples per chunk"
    )
    parser.add_argument(
        "--name-filter",
        type=str,
        default=None,
        help="Substring to filter LSL stream names (LSL backend only)"
    )
    parser.add_argument(
        "--mac-address",
        type=str,
        default=None,
        help="Muse MAC address (BrainFlow backend only)"
    )
    
    args = parser.parse_args()

    run_session(
        backend=args.backend,
        duration_seconds=args.duration,
        output_path=args.output,
        chunk_size=args.chunk_size,
        name_filter=args.name_filter,
        mac_address=args.mac_address,
    )


if __name__ == "__main__":
    main()
