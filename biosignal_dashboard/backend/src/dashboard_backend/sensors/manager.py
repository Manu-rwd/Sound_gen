"""Sensor manager for coordinating all sensor runners."""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..models.descriptors import SensorDescriptor
from ..models.messages import SampleBatch
from .base_runner import BaseSensorRunner
from .fake_runner import (
    create_fake_eeg_runner,
    create_fake_gsr_runner,
    create_fake_ecg_runner,
)

logger = logging.getLogger(__name__)


@dataclass
class SensorConfig:
    """Configuration for real sensor connections."""
    
    # Muse EEG
    use_muse_eeg: bool = False
    muse_backend: str = "brainflow"  # "brainflow" (direct BLE) or "lsl" (BlueMuse)
    muse_mac_address: Optional[str] = None  # For BrainFlow (optional, auto-discovers)
    muse_name_filter: Optional[str] = None  # For LSL, e.g., "Muse-1AE4"
    
    # GSR
    use_gsr: bool = False
    gsr_port: Optional[str] = None  # e.g., "COM15"
    
    # ECG
    use_ecg: bool = False
    ecg_port: Optional[str] = None  # e.g., "COM4"


class SensorManager:
    """Manages all sensor runners and provides unified access.
    
    Responsibilities:
    - Initialize and hold all sensor runners
    - Provide list of sensor descriptors
    - Enable/disable individual sensors
    - Collect samples from all active sensors
    """
    
    def __init__(
        self,
        use_fake_sensors: bool = True,
        config: Optional[SensorConfig] = None,
    ):
        """Initialize the sensor manager.
        
        Args:
            use_fake_sensors: If True, use simulated sensors for testing.
                             If False, use real hardware based on config.
            config: Configuration for real sensors (required if use_fake_sensors=False).
        """
        self._runners: Dict[str, BaseSensorRunner] = {}
        self._use_fake_sensors = use_fake_sensors
        self._config = config or SensorConfig()
        
        self._init_sensors()
    
    def _init_sensors(self) -> None:
        """Initialize all sensor runners."""
        if self._use_fake_sensors:
            self._init_fake_sensors()
        else:
            self._init_real_sensors()
    
    def _init_fake_sensors(self) -> None:
        """Initialize fake sensors for testing."""
        eeg_runner = create_fake_eeg_runner()
        gsr_runner = create_fake_gsr_runner()
        ecg_runner = create_fake_ecg_runner()
        
        self._runners[eeg_runner.device_id] = eeg_runner
        self._runners[gsr_runner.device_id] = gsr_runner
        self._runners[ecg_runner.device_id] = ecg_runner
        
        logger.info("Initialized fake sensors for testing")
    
    def _init_real_sensors(self) -> None:
        """Initialize real hardware sensors based on config."""
        if self._config.use_muse_eeg:
            self._init_muse_eeg()
        
        if self._config.use_gsr and self._config.gsr_port:
            self._init_gsr()
        
        if self._config.use_ecg and self._config.ecg_port:
            self._init_ecg()
        
        if not self._runners:
            logger.warning("No real sensors configured, falling back to fake sensors")
            self._init_fake_sensors()
    
    def _init_muse_eeg(self) -> None:
        """Initialize Muse EEG runner."""
        try:
            from .muse_eeg_runner import create_muse_eeg_runner
            
            backend = self._config.muse_backend
            runner = create_muse_eeg_runner(
                backend=backend,  # type: ignore
                mac_address=self._config.muse_mac_address,
                name_filter=self._config.muse_name_filter,
            )
            
            self._runners[runner.device_id] = runner
            logger.info(f"Initialized Muse EEG runner (backend: {backend})")
            
        except ImportError as e:
            logger.error(f"Failed to import dependencies for Muse EEG: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Muse EEG: {e}")
    
    def _init_gsr(self) -> None:
        """Initialize GSR runner."""
        try:
            from gsr_hub.acquisition.gsr_source import GSRSource
            from .gsr_runner import GSRRunner, create_gsr_descriptor
            
            source = GSRSource(port=self._config.gsr_port)
            descriptor = create_gsr_descriptor(self._config.gsr_port)
            runner = GSRRunner(descriptor=descriptor, source=source)
            
            self._runners[runner.device_id] = runner
            logger.info(f"Initialized GSR runner on {self._config.gsr_port}")
            
        except ImportError as e:
            logger.error(f"Failed to import gsr_hub for GSR: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize GSR: {e}")
    
    def _init_ecg(self) -> None:
        """Initialize ECG runner."""
        try:
            from ecg_hub.acquisition.ecg_source import ECGSource
            from ecg_hub.acquisition.ecg_serial_client import ECGSerialClient
            from ecg_hub.interfaces import StreamInfo
            from .ecg_runner import ECGRunner, create_ecg_descriptor
            
            client = ECGSerialClient(port=self._config.ecg_port)
            stream_info = StreamInfo(
                name="Teensy ECG",
                sensor_type="ECG",
                channel_labels=["ECG"],
                sampling_rate_hz=250.0,
            )
            source = ECGSource(client=client, stream_info=stream_info)
            descriptor = create_ecg_descriptor(self._config.ecg_port)
            runner = ECGRunner(descriptor=descriptor, source=source)
            
            self._runners[runner.device_id] = runner
            logger.info(f"Initialized ECG runner on {self._config.ecg_port}")
            
        except ImportError as e:
            logger.error(f"Failed to import ecg_hub for ECG: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize ECG: {e}")
    
    def descriptors(self) -> List[SensorDescriptor]:
        """Get descriptors for all registered sensors."""
        return [runner.descriptor for runner in self._runners.values()]
    
    def get_descriptor(self, device_id: str) -> Optional[SensorDescriptor]:
        """Get descriptor for a specific device."""
        runner = self._runners.get(device_id)
        return runner.descriptor if runner else None
    
    async def enable(self, device_id: str) -> bool:
        """Enable (start) a sensor by device ID.
        
        Args:
            device_id: The sensor's device ID.
            
        Returns:
            True if successful, False if device not found.
        """
        runner = self._runners.get(device_id)
        if runner is None:
            return False
        
        if not runner.running:
            try:
                await runner.start()
                runner.descriptor.enabled = True
                logger.info(f"Enabled sensor: {device_id}")
            except Exception as e:
                logger.error(f"Failed to enable sensor {device_id}: {e}")
                return False
        
        return True
    
    async def disable(self, device_id: str) -> bool:
        """Disable (stop) a sensor by device ID.
        
        Args:
            device_id: The sensor's device ID.
            
        Returns:
            True if successful, False if device not found.
        """
        runner = self._runners.get(device_id)
        if runner is None:
            return False
        
        if runner.running:
            await runner.stop()
            runner.descriptor.enabled = False
            logger.info(f"Disabled sensor: {device_id}")
        
        return True
    
    async def disable_all(self) -> None:
        """Disable all sensors."""
        for device_id in self._runners:
            await self.disable(device_id)
    
    def drain_all_samples(self) -> List[SampleBatch]:
        """Drain samples from all active sensors.
        
        Returns:
            List of SampleBatch objects, one per sensor with data.
        """
        batches: List[SampleBatch] = []
        
        for runner in self._runners.values():
            if runner.running:
                batch = runner.drain_buffer()
                if batch is not None:
                    batches.append(batch)
        
        return batches
    
    def is_enabled(self, device_id: str) -> bool:
        """Check if a sensor is enabled."""
        runner = self._runners.get(device_id)
        return runner.running if runner else False
