"""ECG runner wrapping ECGSource from ecg_hub."""

from __future__ import annotations
import asyncio
import time
import logging
from typing import Optional
import numpy as np

from ..models.descriptors import SensorDescriptor, ChannelInfo
from ..models.messages import SampleBatch
from .base_runner import BaseSensorRunner

logger = logging.getLogger(__name__)


class ECGRunner(BaseSensorRunner):
    """Sensor runner for Teensy ECG via serial (ecg_hub).
    
    Wraps the ECGSource from ecg_hub to provide
    async streaming compatible with the dashboard.
    """
    
    def __init__(
        self,
        descriptor: SensorDescriptor,
        source: "ECGSource",  # type: ignore
        chunk_size: int = 25,
    ):
        """Initialize the ECG runner.
        
        Args:
            descriptor: Sensor metadata.
            source: ECGSource instance from ecg_hub.
            chunk_size: Number of samples to read per chunk.
        """
        super().__init__(descriptor)
        self._source = source
        self._chunk_size = chunk_size
    
    async def _connect(self) -> None:
        """Connect to the ECG device via serial."""
        loop = asyncio.get_running_loop()
        logger.info("Connecting to ECG device...")
        
        try:
            await loop.run_in_executor(None, self._source.connect)
            logger.info("ECG device connected")
        except Exception as e:
            logger.error(f"Failed to connect to ECG device: {e}")
            raise
    
    async def _disconnect(self) -> None:
        """Disconnect from the ECG device."""
        loop = asyncio.get_running_loop()
        
        try:
            await loop.run_in_executor(None, self._source.close)
            logger.info("ECG device disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting ECG device: {e}")
    
    async def _loop(self) -> None:
        """Main acquisition loop for ECG data."""
        loop = asyncio.get_running_loop()
        
        try:
            while self._running:
                # Read chunk in executor
                result = await loop.run_in_executor(
                    None,
                    self._source.read_chunk,
                    self._chunk_size,
                )
                
                # result is dict with 'timestamps', 'values', 'status_flags'
                values = result.get("values", [])
                
                if not values:
                    await asyncio.sleep(0.02)
                    continue
                
                # Convert to numpy array shape (n_samples,) for single channel
                data = np.array(values, dtype=np.float32)
                
                ts = time.time()
                self._buffer.append(ts, data)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"ECG loop error: {e}")
            self._running = False


def create_ecg_descriptor(port: str = "COM?") -> SensorDescriptor:
    """Create a SensorDescriptor for ECG.
    
    Args:
        port: COM port name.
    
    Returns:
        SensorDescriptor for ECG.
    """
    return SensorDescriptor(
        id="ecg_teensy",
        name=f"Teensy ECG ({port})",
        kind="ECG",
        channels=[
            ChannelInfo(id="ECG", label="ECG Lead", unit="mV"),
        ],
        sampling_rate=250.0,
        backend="serial",
        enabled=False,
    )
