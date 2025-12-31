from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Iterator
import time

import serial  # from pyserial


@dataclass
class GSRSample:
    """One GSR sample from the Teensy stream."""
    t_device_ms: int  # millis since boot, from Teensy
    t_host: float     # host timestamp (time.time()) when line received
    value_raw: int    # raw ADC-ish GSR value (e.g., 0..4095)


class GSRSerialClient:
    """Low-level serial client for reading GSR data from Teensy."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 0.1,
        sensor_label: str = "GSR",
    ) -> None:
        self._port_name = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._sensor_label = sensor_label
        self._serial: Optional[serial.Serial] = None

    def open(self) -> None:
        """Open the serial port and clear any buffered data."""
        if self._serial is not None and self._serial.is_open:
            return

        self._serial = serial.Serial(
            self._port_name,
            baudrate=self._baudrate,
            timeout=self._timeout,
        )
        # Teensy sometimes resets on open; give it a moment
        time.sleep(0.5)
        self._serial.reset_input_buffer()

    def close(self) -> None:
        """Close the serial port."""
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def _parse_line(self, line: str) -> Optional[GSRSample]:
        """
        Parse a line like: '43534,GSR,2555'.
        Returns GSRSample or None if malformed / different label.
        """
        parts = line.strip().split(",")
        if len(parts) != 3:
            return None

        try:
            t_device_ms = int(parts[0])
            label = parts[1]
            value_raw = int(parts[2])
        except ValueError:
            return None

        if label != self._sensor_label:
            return None

        return GSRSample(
            t_device_ms=t_device_ms,
            t_host=time.time(),
            value_raw=value_raw,
        )

    def read_samples(self) -> Iterator[GSRSample]:
        """
        Infinite iterator over valid GSRSample objects.

        NOTE: The serial port must be opened first via open().
        """
        if self._serial is None:
            raise RuntimeError("Serial port not open; call open() first.")

        while True:
            line_bytes = self._serial.readline()
            if not line_bytes:
                # timeout reached; just loop again
                continue

            line = line_bytes.decode(errors="ignore")
            sample = self._parse_line(line)
            if sample is not None:
                yield sample
