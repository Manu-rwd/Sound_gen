"""ECG source wrapper implementing SensorSource."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ecg_hub.acquisition.ecg_serial_client import ECGSerialClient
from ecg_hub.interfaces import SensorSource, StreamInfo


class ECGSource(SensorSource):
    """High-level chunked ECG source implementing SensorSource interface."""

    def __init__(
        self,
        client: ECGSerialClient,
        stream_info: StreamInfo,
        max_queue: Optional[int] = None,
    ):
        self._client = client
        self._stream_info = stream_info
        self._max_queue = max_queue
        self._start_time: Optional[float] = None

    def connect(self) -> None:
        """Connect to the ECG source."""
        self._client.open()
        self._start_time = time.time()

    def read_chunk(self, max_samples: int) -> Dict[str, Any]:
        """
        Read a chunk of ECG samples.

        Returns a dict with:
          - timestamps: list of floats (seconds since start)
          - values: list of ints (ECG values)
          - status_flags: list of strings (or empty if no status)
        """
        timestamps: List[float] = []
        values: List[int] = []
        status_flags: List[str] = []

        samples_collected = 0
        timeout_start = time.time()
        timeout_duration = 5.0  # 5 second timeout for chunk collection

        while samples_collected < max_samples:
            # Check for timeout
            if time.time() - timeout_start > timeout_duration:
                break

            sample = self._client.read_sample()
            if sample is None:
                continue

            # Convert timestamp to seconds since start
            if sample.timestamp_ms is not None:
                ts = sample.timestamp_ms / 1000.0
            else:
                # Use monotonic time if no timestamp available
                ts = time.time() - (self._start_time or time.time())

            timestamps.append(ts)
            values.append(sample.value)
            if sample.status is not None:
                status_flags.append(sample.status)
            else:
                status_flags.append("")

            samples_collected += 1

        return {
            "timestamps": timestamps,
            "values": values,
            "status_flags": status_flags,
        }

    def close(self) -> None:
        """Close the ECG source."""
        self._client.close()
