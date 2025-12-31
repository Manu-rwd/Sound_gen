from __future__ import annotations
from typing import Sequence, List
import time

from .interfaces import SensorSource, StreamInfo
from .gsr_serial_client import GSRSerialClient, GSRSample


class GSRSource(SensorSource):
    """SensorSource wrapper around a GSRSerialClient."""

    def __init__(
        self,
        port: str,
        label: str = "GSR",
        nominal_srate: float = 50.0,
        name: str = "Teensy-GSR",
        source_id: str = "gsr_serial",
    ) -> None:
        self._client = GSRSerialClient(port=port, sensor_label=label)
        self._nominal_srate = nominal_srate
        self._info = StreamInfo(
            name=name,
            type="GSR",
            channel_count=1,
            nominal_srate=nominal_srate,
            source_id=source_id,
        )
        self._iterator = None

    @property
    def stream_info(self) -> StreamInfo:
        return self._info

    def connect(self) -> None:
        """Open the serial port connection."""
        self._client.open()

    def start(self) -> None:
        """Start streaming data from the device."""
        self._iterator = self._client.read_samples()

    def next_chunk(self, max_samples: int) -> tuple[Sequence[list[float]], float, float]:
        """
        Return up to max_samples samples.

        Returns:
            (samples, t_start, t_end)
            - samples: list of [gsr_value] rows
            - t_start: timestamp of first sample
            - t_end: timestamp of last sample
        """
        if self._iterator is None:
            raise RuntimeError("Call start() before next_chunk().")

        samples: List[list[float]] = []
        t_start = time.time()
        t_end = t_start

        for _ in range(max_samples):
            sample: GSRSample = next(self._iterator)
            samples.append([float(sample.value_raw)])
            t_end = sample.t_host

        return samples, t_start, t_end

    def stop(self) -> None:
        """Stop streaming but keep connection available."""
        self._iterator = None

    def close(self) -> None:
        """Clean up the serial connection."""
        self._client.close()
