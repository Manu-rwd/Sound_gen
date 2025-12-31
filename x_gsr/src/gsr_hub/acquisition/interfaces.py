from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass
class StreamInfo:
    """Static metadata about a sensor stream."""
    name: str
    type: str
    channel_count: int
    nominal_srate: float
    source_id: str


class SensorSource(Protocol):
    """
    Generic sensor source interface for time-series devices (GSR, EEG, etc.).
    """

    def connect(self) -> None:
        """Prepare hardware / connection, but do not start streaming yet."""
        ...

    def start(self) -> None:
        """Start streaming data from the device."""
        ...

    def next_chunk(self, max_samples: int) -> tuple[Sequence[list[float]], float, float]:
        """
        Return up to max_samples samples per channel.

        Returns:
            (samples, t_start, t_end)
            - samples: list of rows [ch0, ch1, ..., chN], shape ~ (n_samples, n_channels)
            - t_start: wall-clock timestamp of first sample in the chunk (time.time())
            - t_end: wall-clock timestamp of last sample in the chunk
        """
        ...

    def stop(self) -> None:
        """Stop streaming but keep connection available for later reuse."""
        ...

    def close(self) -> None:
        """Clean up connections, ports, etc."""
        ...

    @property
    def stream_info(self) -> StreamInfo:
        """Static metadata describing this stream."""
        ...
