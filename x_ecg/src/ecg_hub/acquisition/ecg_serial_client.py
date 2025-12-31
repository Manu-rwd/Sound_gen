"""ECG serial client for Teensy AD8232."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import serial


@dataclass
class ECGSample:
    """Represents a single ECG sample."""

    timestamp_ms: Optional[int]
    value: int
    status: Optional[str]


class ECGSerialClient:
    """Low-level serial client for Teensy AD8232 ECG data."""

    def __init__(self, port_name: str, baudrate: int = 115200, timeout: float = 1.0):
        self._port_name = port_name
        self._baudrate = baudrate
        self._timeout = timeout
        self._serial: Optional[serial.Serial] = None

    def open(self) -> None:
        """Open the serial port."""
        if self._serial is not None:
            return
        self._serial = serial.Serial(
            self._port_name,
            baudrate=self._baudrate,
            timeout=self._timeout,
        )

    def close(self) -> None:
        """Close the serial port."""
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def read_sample(self) -> Optional[ECGSample]:
        """
        Read and parse one line; return None if timeout or malformed.

        Supported formats:
        - millis,ECG,value,status  (e.g., "12345,ECG,4028,OK")
        - millis,ECG,value         (e.g., "12345,ECG,4028")
        - value                    (e.g., "4028")
        """
        if self._serial is None:
            raise RuntimeError("Serial port is not open")

        line = self._serial.readline().decode("ascii", errors="ignore").strip()
        if not line:
            return None

        # Try full format: millis,ECG,value[,status]
        parts = line.split(",")
        try:
            if len(parts) == 4 and parts[1].upper() == "ECG":
                ts = int(parts[0])
                value = int(parts[2])
                status = parts[3].strip().upper()
                return ECGSample(timestamp_ms=ts, value=value, status=status)
            elif len(parts) == 3 and parts[1].upper() == "ECG":
                ts = int(parts[0])
                value = int(parts[2])
                return ECGSample(timestamp_ms=ts, value=value, status=None)
            elif len(parts) == 1:
                value = int(parts[0])
                return ECGSample(timestamp_ms=None, value=value, status=None)
        except ValueError:
            # fallthrough to None
            return None

        return None
