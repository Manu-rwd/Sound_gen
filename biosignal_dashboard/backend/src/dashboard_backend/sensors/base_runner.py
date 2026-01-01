"""Base class for sensor runners."""

from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

from ..models.descriptors import SensorDescriptor
from ..models.messages import SampleBatch
from .ring_buffer import RingBuffer


class BaseSensorRunner(ABC):
    """Abstract base class for sensor data acquisition runners.
    
    Each runner wraps a sensor source and provides:
    - Async start/stop for lifecycle management
    - Internal ring buffer for samples
    - drain_buffer() to extract samples as SampleBatch
    
    Subclasses must implement:
    - _connect(): Establish connection to the sensor
    - _disconnect(): Clean up the connection
    - _loop(): Main acquisition loop
    """
    
    def __init__(self, descriptor: SensorDescriptor, buffer_maxlen: int = 4096):
        """Initialize the sensor runner.
        
        Args:
            descriptor: Metadata about this sensor.
            buffer_maxlen: Maximum samples to buffer before trimming.
        """
        self.descriptor = descriptor
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._buffer = RingBuffer(maxlen=buffer_maxlen)
    
    @property
    def running(self) -> bool:
        """Check if the runner is currently active."""
        return self._running
    
    @property
    def device_id(self) -> str:
        """Get the device ID from the descriptor."""
        return self.descriptor.id
    
    async def start(self) -> None:
        """Start the sensor runner.
        
        Connects to the sensor and starts the acquisition loop.
        """
        if self._running:
            return
        
        self._running = True
        await self._connect()
        self._task = asyncio.create_task(self._loop())
    
    async def stop(self) -> None:
        """Stop the sensor runner.
        
        Cancels the acquisition loop and disconnects from the sensor.
        """
        if not self._running:
            return
        
        self._running = False
        
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        await self._disconnect()
    
    @abstractmethod
    async def _connect(self) -> None:
        """Connect to the sensor hardware.
        
        Override in subclass to implement connection logic.
        For blocking operations, use loop.run_in_executor().
        """
        pass
    
    @abstractmethod
    async def _disconnect(self) -> None:
        """Disconnect from the sensor hardware.
        
        Override in subclass to implement cleanup logic.
        """
        pass
    
    @abstractmethod
    async def _loop(self) -> None:
        """Main acquisition loop.
        
        Override in subclass to implement the data reading loop.
        Should check self._running and exit when False.
        Use self._buffer.append(timestamp, data) to store samples.
        """
        pass
    
    def drain_buffer(self) -> Optional[SampleBatch]:
        """Extract all buffered samples as a SampleBatch.
        
        Returns:
            SampleBatch if samples are available, None otherwise.
        """
        if self._buffer.is_empty():
            return None
        
        timestamps, chunks = self._buffer.consume_all()
        
        if not chunks:
            return None
        
        # Merge chunks into a single array
        # Expected shape for multi-channel: (n_samples, n_channels)
        # Expected shape for single-channel: (n_samples,)
        try:
            if chunks[0].ndim == 1:
                # Single-channel sensor (e.g., GSR)
                data = np.concatenate(chunks)
                # Convert to [n_samples][1] format
                values = [[float(v)] for v in data]
            else:
                # Multi-channel sensor (e.g., EEG)
                data = np.vstack(chunks)  # shape (n_samples, n_channels)
                values = data.tolist()
        except Exception:
            # If concatenation fails, try simpler approach
            values = []
            for chunk in chunks:
                if chunk.ndim == 1:
                    for v in chunk:
                        values.append([float(v)])
                else:
                    for row in chunk:
                        values.append([float(v) for v in row])
        
        return SampleBatch(
            deviceId=self.descriptor.id,
            timestamp=timestamps[0],
            channels=[ch.id for ch in self.descriptor.channels],
            samplingRate=self.descriptor.sampling_rate,
            values=values,
        )
