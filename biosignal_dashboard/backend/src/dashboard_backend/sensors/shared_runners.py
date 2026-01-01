"""Runners that use the TeensyMultiplexer for shared serial access."""

from __future__ import annotations
import logging
import asyncio
import numpy as np
from typing import Optional

from ..models.descriptors import SensorDescriptor
from .base_runner import BaseSensorRunner
from .teensy_multiplexer import TeensyMultiplexer

logger = logging.getLogger(__name__)

class SharedTeensyRunner(BaseSensorRunner):
    """Base class for sensors sharing a Teensy port."""
    
    def __init__(self, descriptor: SensorDescriptor, port: str):
        super().__init__(descriptor)
        self.port = port
        self.multiplexer = TeensyMultiplexer.get_instance(port)
        self.label = descriptor.kind # "GSR" or "ECG"
        
        # Register callback
        self.multiplexer.register_callback(self.label, self._handle_sample)
        
    def _handle_sample(self, timestamp: float, value: float):
        """Callback from multiplexer."""
        if not self._running:
            return
            
        # Push to ring buffer (RingBuffer expects np.array)
        data = np.array([value], dtype=np.float32)
        self._buffer.append(timestamp, data)
        
    async def _connect(self):
        """Start the multiplexer if not started."""
        await self.multiplexer.start()
        
    async def _disconnect(self):
        """
        We don't stop the multiplexer here because other sensors might use it.
        Ideally we would refcount, but for now we keep it running.
        """
        pass # Multiplexer stays alive
        
    async def _loop(self):
        """
        No-op, as data is pushed via callback.
        We just need to keep the runner 'active'.
        """
        while self._running:
            await asyncio.sleep(1)

class SharedGSRRunner(SharedTeensyRunner):
    """GSR implementation of shared runner."""
    pass

class SharedECGRunner(SharedTeensyRunner):
    """ECG implementation of shared runner."""
    pass
