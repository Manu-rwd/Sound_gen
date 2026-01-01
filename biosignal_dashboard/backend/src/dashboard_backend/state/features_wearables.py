"""Wearable feature adapter for future sensor integration.

Provides a standardized interface for wearable devices like
Pixel Watch, smart rings, and fitness bands.

Currently a stub - returns empty dict. Implement adapters as
wearable integrations are added.
"""

from __future__ import annotations
from typing import Dict, Optional, Any, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


@dataclass
class WearableFeatures:
    """Standardized features from wearable devices."""
    
    # Heart rate (backup/complement to ECG)
    wear_hr: Optional[float] = None                # Current HR
    wear_hrv_rmssd_1min: Optional[float] = None    # HRV if RR exposed
    
    # Activity
    wear_activity_level: Optional[str] = None      # "rest", "light", "intense"
    wear_step_count: Optional[int] = None          # Steps if available
    
    # Temperature
    wear_temp: Optional[float] = None              # Skin temp (°C)
    wear_temp_deviation: Optional[float] = None    # Deviation from baseline
    
    # EDA (for devices with electrodermal sensing)
    wear_eda_scl: Optional[float] = None           # Tonic level
    wear_eda_scr_count: Optional[float] = None     # SCR count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def is_empty(self) -> bool:
        """Check if all features are None."""
        return all(v is None for v in self.__dict__.values())


class WearableAdapter(ABC):
    """Abstract base class for wearable device adapters."""
    
    @property
    @abstractmethod
    def device_name(self) -> str:
        """Human-readable device name."""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if device is currently connected."""
        pass
    
    @abstractmethod
    def compute_features(self) -> WearableFeatures:
        """Compute current features from device data."""
        pass


class StubWearableAdapter(WearableAdapter):
    """Stub adapter that returns empty features.
    
    Use this as a placeholder until real wearable integration is added.
    """
    
    @property
    def device_name(self) -> str:
        return "None"
    
    @property
    def is_connected(self) -> bool:
        return False
    
    def compute_features(self) -> WearableFeatures:
        return WearableFeatures()


class WearableFeatureAdapter:
    """
    Main adapter that aggregates features from all connected wearables.
    
    Can manage multiple wearable devices and combine their features.
    Currently uses stub - real adapters to be added for:
    - Pixel Watch 3 (via Health Services API)
    - Smart rings (Oura, etc.)
    - Fitness bands
    """
    
    def __init__(self):
        self._adapters: Dict[str, WearableAdapter] = {}
        self._stub = StubWearableAdapter()
    
    def register_adapter(self, adapter_id: str, adapter: WearableAdapter) -> None:
        """Register a wearable adapter."""
        self._adapters[adapter_id] = adapter
        logger.info(f"Registered wearable adapter: {adapter.device_name}")
    
    def unregister_adapter(self, adapter_id: str) -> None:
        """Unregister a wearable adapter."""
        if adapter_id in self._adapters:
            del self._adapters[adapter_id]
    
    def compute(self) -> Dict[str, Any]:
        """
        Compute aggregated features from all connected wearables.
        
        Returns:
            Dict of feature values (empty if no wearables connected)
        """
        if not self._adapters:
            return {}
        
        # Collect features from all connected adapters
        all_features = WearableFeatures()
        
        for adapter_id, adapter in self._adapters.items():
            if adapter.is_connected:
                try:
                    features = adapter.compute_features()
                    # Merge features (later values override)
                    for key, value in features.to_dict().items():
                        if value is not None:
                            setattr(all_features, key, value)
                except Exception as e:
                    logger.warning(f"Error computing features from {adapter.device_name}: {e}")
        
        return all_features.to_dict()
    
    @property
    def connected_devices(self) -> list[str]:
        """List names of currently connected devices."""
        return [
            adapter.device_name
            for adapter in self._adapters.values()
            if adapter.is_connected
        ]


# ============================================================================
# Example adapter templates for future implementation
# ============================================================================

class PixelWatchAdapter(WearableAdapter):
    """Template for Pixel Watch 3 integration.
    
    Would connect via Health Services API or companion app bridge.
    """
    
    def __init__(self):
        self._connected = False
        # TODO: Initialize connection to Pixel Watch
    
    @property
    def device_name(self) -> str:
        return "Pixel Watch 3"
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def compute_features(self) -> WearableFeatures:
        # TODO: Read actual data from Pixel Watch
        return WearableFeatures()


class OuraRingAdapter(WearableAdapter):
    """Template for Oura Ring integration.
    
    Would connect via Oura Cloud API.
    """
    
    def __init__(self, api_token: Optional[str] = None):
        self._api_token = api_token
        self._connected = False
    
    @property
    def device_name(self) -> str:
        return "Oura Ring"
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._api_token is not None
    
    def compute_features(self) -> WearableFeatures:
        # TODO: Read actual data from Oura API
        return WearableFeatures()
