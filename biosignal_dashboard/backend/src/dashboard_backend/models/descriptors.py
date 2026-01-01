"""Sensor descriptor models."""

from pydantic import BaseModel
from typing import Literal, List, Optional


SensorKind = Literal["EEG", "ECG", "GSR", "HR", "ACCEL", "OTHER"]


class ChannelInfo(BaseModel):
    """Information about a single sensor channel."""
    
    id: str
    label: str
    unit: Optional[str] = None


class SensorDescriptor(BaseModel):
    """Metadata describing a sensor device."""
    
    id: str                     # e.g. "eeg_muse", "gsr_teensy"
    name: str                   # Human-readable name
    kind: SensorKind
    channels: List[ChannelInfo]
    sampling_rate: float
    backend: str                # e.g. "lsl", "serial", "fake"
    enabled: bool = False
