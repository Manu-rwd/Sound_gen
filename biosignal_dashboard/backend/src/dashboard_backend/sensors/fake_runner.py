"""Fake sensor runner for testing and development."""

from __future__ import annotations
import asyncio
import time
import math
import numpy as np

from ..models.descriptors import SensorDescriptor, ChannelInfo
from .base_runner import BaseSensorRunner


class FakeSensorRunner(BaseSensorRunner):
    """A simulated sensor that generates sine waves for testing.
    
    Generates multi-channel sinusoidal data at the configured sampling rate.
    Useful for testing the pipeline without real hardware.
    """
    
    def __init__(
        self,
        descriptor: SensorDescriptor,
        frequencies: list[float] | None = None,
        amplitude: float = 100.0,
        noise_level: float = 10.0,
        chunk_size: int = 16,
    ):
        """Initialize the fake sensor.
        
        Args:
            descriptor: Sensor metadata.
            frequencies: List of frequencies (Hz) for each channel.
                        Defaults to [10, 12, 8, 15] for 4 channels.
            amplitude: Signal amplitude.
            noise_level: Standard deviation of Gaussian noise.
            chunk_size: Number of samples per chunk.
        """
        super().__init__(descriptor)
        
        n_channels = len(descriptor.channels)
        self._frequencies = frequencies or [10 + i * 2 for i in range(n_channels)]
        self._amplitude = amplitude
        self._noise_level = noise_level
        self._chunk_size = chunk_size
        self._sample_index = 0
    
    async def _connect(self) -> None:
        """Simulated connection (no-op)."""
        self._sample_index = 0
    
    async def _disconnect(self) -> None:
        """Simulated disconnection (no-op)."""
        pass
    
    async def _loop(self) -> None:
        """Generate simulated sensor data."""
        sample_rate = self.descriptor.sampling_rate
        chunk_duration = self._chunk_size / sample_rate
        n_channels = len(self.descriptor.channels)
        
        try:
            while self._running:
                # Generate time points for this chunk
                t_start = self._sample_index / sample_rate
                t_points = np.linspace(
                    t_start,
                    t_start + chunk_duration,
                    self._chunk_size,
                    endpoint=False
                )
                
                # Generate sinusoidal data for each channel
                data = np.zeros((self._chunk_size, n_channels), dtype=np.float32)
                for ch_idx, freq in enumerate(self._frequencies[:n_channels]):
                    signal = self._amplitude * np.sin(2 * np.pi * freq * t_points)
                    noise = np.random.normal(0, self._noise_level, self._chunk_size)
                    data[:, ch_idx] = signal + noise
                
                # Store in buffer
                timestamp = time.time()
                self._buffer.append(timestamp, data)
                
                self._sample_index += self._chunk_size
                
                # Sleep to match real-time rate
                await asyncio.sleep(chunk_duration)
                
        except asyncio.CancelledError:
            pass


def create_fake_eeg_runner() -> FakeSensorRunner:
    """Create a fake EEG runner mimicking Muse headband."""
    descriptor = SensorDescriptor(
        id="fake_eeg",
        name="Fake EEG (Simulated Muse)",
        kind="EEG",
        channels=[
            ChannelInfo(id="TP9", label="TP9", unit="µV"),
            ChannelInfo(id="AF7", label="AF7", unit="µV"),
            ChannelInfo(id="AF8", label="AF8", unit="µV"),
            ChannelInfo(id="TP10", label="TP10", unit="µV"),
        ],
        sampling_rate=256.0,
        backend="fake",
        enabled=False,
    )
    return FakeSensorRunner(
        descriptor=descriptor,
        frequencies=[10.0, 12.0, 8.0, 15.0],  # Alpha-ish frequencies
        amplitude=50.0,
        noise_level=5.0,
        chunk_size=32,
    )


def create_fake_gsr_runner() -> FakeSensorRunner:
    """Create a fake GSR runner mimicking Teensy GSR."""
    descriptor = SensorDescriptor(
        id="fake_gsr",
        name="Fake GSR (Simulated Teensy)",
        kind="GSR",
        channels=[
            ChannelInfo(id="GSR", label="Skin Conductance", unit="µS"),
        ],
        sampling_rate=50.0,
        backend="fake",
        enabled=False,
    )
    return FakeSensorRunner(
        descriptor=descriptor,
        frequencies=[0.1],  # Very slow drift
        amplitude=2.0,      # Typical GSR range
        noise_level=0.1,
        chunk_size=8,
    )


def create_fake_ecg_runner() -> FakeSensorRunner:
    """Create a fake ECG runner mimicking Teensy ECG."""
    descriptor = SensorDescriptor(
        id="fake_ecg",
        name="Fake ECG (Simulated Teensy)",
        kind="ECG",
        channels=[
            ChannelInfo(id="ECG", label="ECG Lead", unit="mV"),
        ],
        sampling_rate=250.0,
        backend="fake",
        enabled=False,
    )
    return FakeSensorRunner(
        descriptor=descriptor,
        frequencies=[1.2],  # ~72 BPM heart rate
        amplitude=1.0,
        noise_level=0.05,
        chunk_size=25,
    )
