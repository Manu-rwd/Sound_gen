"""WebSocket message schemas."""

from pydantic import BaseModel
from typing import Literal, List, Optional, Union


class SampleBatch(BaseModel):
    """A batch of samples from a single sensor."""
    
    deviceId: str
    timestamp: float            # Unix seconds for first sample
    channels: List[str]         # Channel IDs
    samplingRate: float
    values: List[List[float]]   # shape: [n_samples][n_channels]


class SamplesMessage(BaseModel):
    """WebSocket message containing sample batches from all active sensors."""
    
    type: Literal["samples"] = "samples"
    payload: List[SampleBatch]


class DescriptorsMessage(BaseModel):
    """WebSocket message containing sensor descriptors."""
    
    type: Literal["descriptors"] = "descriptors"
    payload: List[dict]  # List of SensorDescriptor as dicts


class StateScores(BaseModel):
    """Focus/stress/relaxation scores."""
    
    focus: float        # 0–1
    stress: float       # 0–1
    relaxation: float   # 0–1


class StateEstimate(BaseModel):
    """State estimation message."""
    
    type: Literal["state"] = "state"
    timestamp: float
    scores: StateScores
    label: Optional[str] = None
    explanation: Optional[str] = None


class AudioEvent(BaseModel):
    """Audio playback event."""
    
    timestamp: float
    event: Literal["start", "stop", "tag"]
    trackId: Optional[str] = None
    trackName: Optional[str] = None
    tags: Optional[List[str]] = None


class AudioMessage(BaseModel):
    """WebSocket message for audio events."""
    
    type: Literal["audio"] = "audio"
    payload: AudioEvent


class ErrorMessage(BaseModel):
    """WebSocket error message."""
    
    type: Literal["error"] = "error"
    message: str
    deviceId: Optional[str] = None


# Control messages (frontend -> backend)
class ControlAction(BaseModel):
    """Control action to enable/disable a device."""
    
    type: Literal["control"] = "control"
    action: Literal["enable", "disable"]
    deviceId: str


class AudioEventAction(BaseModel):
    """Audio event action from frontend."""
    
    type: Literal["audio_event"] = "audio_event"
    event: Literal["start", "stop"]
    trackId: str
    trackName: Optional[str] = None
    tags: Optional[List[str]] = None


# Union type for incoming messages
IncomingMessage = Union[ControlAction, AudioEventAction]
