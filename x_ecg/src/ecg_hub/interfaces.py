"""Shared interfaces for ECG hub."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class StreamInfo:
    """Describes a sensor stream."""

    name: str
    sensor_type: str  # e.g. "ECG"
    channel_labels: List[str]
    sampling_rate_hz: float | None = None


class SensorSource(ABC):
    """Generic chunked sensor source interface."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the sensor source."""
        ...

    @abstractmethod
    def read_chunk(self, max_samples: int) -> Dict[str, Any]:
        """
        Read a chunk of sensor data.

        Return a dict at least containing:
          - "timestamps": list[float]    # seconds since start or ms
          - "values": list[float | int]
          - Optional: "status_flags": list[str] if available
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the sensor source."""
        ...
