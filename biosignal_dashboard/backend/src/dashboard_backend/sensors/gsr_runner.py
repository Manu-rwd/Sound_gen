"""GSR runner wrapping GSRSource from gsr_hub."""

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


class GSRRunner(BaseSensorRunner):
    """Sensor runner for Teensy GSR via serial (gsr_hub).
    
    Wraps the GSRSource from gsr_hub to provide
    async streaming compatible with the dashboard.
    """
    
    def __init__(
        self,
        descriptor: SensorDescriptor,
        source: "GSRSource",  # type: ignore
        chunk_size: int = 16,
    ):
        """Initialize the GSR runner.
        
        Args:
            descriptor: Sensor metadata.
            source: GSRSource instance from gsr_hub.
            chunk_size: Number of samples to read per chunk.
        """
        super().__init__(descriptor)
        self._source = source
        self._chunk_size = chunk_size
    
    async def _connect(self) -> None:
        """Connect to the GSR device via serial."""
        loop = asyncio.get_running_loop()
        logger.info("Connecting to GSR device...")
        
        try:
            await loop.run_in_executor(None, self._source.connect)
            await loop.run_in_executor(None, self._source.start)
            logger.info("GSR device connected and streaming")
        except Exception as e:
            logger.error(f"Failed to connect to GSR device: {e}")
            raise
    
    async def _disconnect(self) -> None:
        """Disconnect from the GSR device."""
        loop = asyncio.get_running_loop()
        
        try:
            await loop.run_in_executor(None, self._source.stop)
            await loop.run_in_executor(None, self._source.close)
            logger.info("GSR device disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting GSR device: {e}")
    
    async def _loop(self) -> None:
        """Main acquisition loop for GSR data."""
        loop = asyncio.get_running_loop()
        
        try:
            while self._running:
                # Read chunk in executor
                result = await loop.run_in_executor(
                    None,
                    self._source.next_chunk,
                    self._chunk_size,
                )
                
                samples, t_start, t_end = result
                
                if not samples:
                    await asyncio.sleep(0.02)
                    continue
                
                # samples is list of [gsr_value] rows
                # Convert to numpy array shape (n_samples,) for single channel
                data = np.array([s[0] for s in samples], dtype=np.float32)
                
                ts = time.time()
                self._buffer.append(ts, data)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"GSR loop error: {e}")
            self._running = False


def create_gsr_descriptor(port: str = "COM?") -> SensorDescriptor:
    """Create a SensorDescriptor for GSR.
    
    Args:
        port: COM port name.
    
    Returns:
        SensorDescriptor for GSR.
    """
    return SensorDescriptor(
        id="gsr_teensy",
        name=f"Teensy GSR ({port})",
        kind="GSR",
        channels=[
            ChannelInfo(id="GSR", label="Skin Conductance", unit="µS"),
        ],
        sampling_rate=50.0,
        backend="serial",
        enabled=False,
    )
