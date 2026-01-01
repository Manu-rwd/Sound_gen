"""Muse EEG runner supporting both LSL and BrainFlow backends."""

from __future__ import annotations
import asyncio
import time
import logging
from typing import Optional, Literal
import numpy as np

from ..models.descriptors import SensorDescriptor, ChannelInfo
from ..models.messages import SampleBatch
from .base_runner import BaseSensorRunner

logger = logging.getLogger(__name__)

# Type alias for backend choice
MuseBackend = Literal["lsl", "brainflow"]


class MuseEEGRunner(BaseSensorRunner):
    """Sensor runner for Muse EEG headband.
    
    Supports two backends:
    - "lsl": Uses MuseLSLEEGSource (requires BlueMuse running)
    - "brainflow": Uses MuseBrainFlowSource (connects directly via Bluetooth)
    
    BrainFlow is recommended for automatic connection without external apps.
    """
    
    def __init__(
        self,
        descriptor: SensorDescriptor,
        backend: MuseBackend = "brainflow",
        mac_address: Optional[str] = None,
        name_filter: Optional[str] = None,
        chunk_size: int = 32,
    ):
        """Initialize the Muse EEG runner.
        
        Args:
            descriptor: Sensor metadata.
            backend: "brainflow" (direct BLE) or "lsl" (via BlueMuse).
            mac_address: MAC address for BrainFlow backend (optional).
            name_filter: Name filter for LSL backend (e.g., "Muse-1AE4").
            chunk_size: Number of samples to read per chunk.
        """
        super().__init__(descriptor)
        self._backend = backend
        self._mac_address = mac_address
        self._name_filter = name_filter
        self._chunk_size = chunk_size
        self._source = None
    
    async def _connect(self) -> None:
        """Connect to the Muse EEG stream."""
        loop = asyncio.get_running_loop()
        logger.info(f"Connecting to Muse EEG via {self._backend}...")
        
        try:
            if self._backend == "brainflow":
                await self._connect_brainflow(loop)
            else:
                await self._connect_lsl(loop)
            
            logger.info(f"Muse EEG connected via {self._backend}")
        except Exception as e:
            logger.error(f"Failed to connect to Muse EEG: {e}")
            raise
    
    async def _connect_brainflow(self, loop: asyncio.AbstractEventLoop) -> None:
        """Connect using BrainFlow (direct Bluetooth)."""
        from sound_gen_hub.acquisition.muse_brainflow import MuseBrainFlowSource
        
        self._source = MuseBrainFlowSource(mac_address=self._mac_address)
        await loop.run_in_executor(None, self._source.connect)
    
    async def _connect_lsl(self, loop: asyncio.AbstractEventLoop) -> None:
        """Connect using LSL (requires BlueMuse)."""
        from sound_gen_hub.acquisition.muse_lsl import MuseLSLEEGSource
        
        self._source = MuseLSLEEGSource(name_filter=self._name_filter)
        await loop.run_in_executor(None, self._source.connect)
    
    async def _disconnect(self) -> None:
        """Disconnect from the Muse EEG stream."""
        if self._source is not None:
            loop = asyncio.get_running_loop()
            
            # BrainFlow source has a close() method
            if hasattr(self._source, 'close'):
                try:
                    await loop.run_in_executor(None, self._source.close)
                except Exception as e:
                    logger.warning(f"Error closing Muse EEG source: {e}")
            
            self._source = None
        
        logger.info("Muse EEG runner disconnected")
    
    async def _loop(self) -> None:
        """Main acquisition loop for Muse EEG data."""
        loop = asyncio.get_running_loop()
        
        try:
            while self._running:
                if self._source is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Read chunk in executor to avoid blocking event loop
                chunk = await loop.run_in_executor(
                    None,
                    self._source.read_chunk,
                    self._chunk_size,
                    0.1,  # timeout (used by LSL, ignored by BrainFlow)
                )
                
                if chunk is None or chunk.data.size == 0:
                    await asyncio.sleep(0.01)
                    continue
                
                # chunk.data shape is (n_channels, n_samples) from both sources
                # We need (n_samples, n_channels) for our buffer
                data = chunk.data.T.astype(np.float32)
                
                ts = time.time()
                self._buffer.append(ts, data)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Muse EEG loop error: {e}")
            self._running = False


def create_muse_eeg_descriptor(
    backend: MuseBackend = "brainflow",
    device_id: str = "",
) -> SensorDescriptor:
    """Create a SensorDescriptor for Muse EEG.
    
    Args:
        backend: "brainflow" or "lsl".
        device_id: Optional device identifier.
    
    Returns:
        SensorDescriptor for Muse EEG.
    """
    name = "Muse EEG"
    if device_id:
        name = f"Muse EEG ({device_id})"
    
    return SensorDescriptor(
        id="eeg_muse",
        name=name,
        kind="EEG",
        channels=[
            ChannelInfo(id="TP9", label="TP9", unit="µV"),
            ChannelInfo(id="AF7", label="AF7", unit="µV"),
            ChannelInfo(id="AF8", label="AF8", unit="µV"),
            ChannelInfo(id="TP10", label="TP10", unit="µV"),
        ],
        sampling_rate=256.0,
        backend=backend,
        enabled=False,
    )


def create_muse_eeg_runner(
    backend: MuseBackend = "brainflow",
    mac_address: Optional[str] = None,
    name_filter: Optional[str] = None,
) -> MuseEEGRunner:
    """Factory function to create a MuseEEGRunner.
    
    Args:
        backend: "brainflow" (recommended) or "lsl".
        mac_address: MAC address for BrainFlow (optional, will auto-discover).
        name_filter: Name filter for LSL (e.g., "Muse-1AE4").
    
    Returns:
        Configured MuseEEGRunner.
    """
    device_id = mac_address or name_filter or "auto"
    descriptor = create_muse_eeg_descriptor(backend=backend, device_id=device_id)
    
    return MuseEEGRunner(
        descriptor=descriptor,
        backend=backend,
        mac_address=mac_address,
        name_filter=name_filter,
    )
