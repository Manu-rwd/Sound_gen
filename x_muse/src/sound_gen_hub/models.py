"""Core data models for EEG acquisition."""

from dataclasses import dataclass, asdict
from typing import Any, Dict
import numpy as np
from pydantic import BaseModel


@dataclass
class StreamMeta:
    """Metadata about an EEG stream."""
    
    name: str
    type: str
    channel_count: int
    nominal_srate: float
    source_id: str | None = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class SampleChunk:
    """A chunk of EEG samples with timestamps."""
    
    meta: StreamMeta
    timestamps: np.ndarray  # shape (n_samples,)
    data: np.ndarray        # shape (n_channels, n_samples)
    
    def __post_init__(self):
        """Validate shapes."""
        if self.timestamps.ndim != 1:
            raise ValueError(f"timestamps must be 1D, got shape {self.timestamps.shape}")
        if self.data.ndim != 2:
            raise ValueError(f"data must be 2D, got shape {self.data.shape}")
        if self.data.shape[0] != self.meta.channel_count:
            raise ValueError(
                f"data channel count {self.data.shape[0]} != "
                f"meta.channel_count {self.meta.channel_count}"
            )
        if self.data.shape[1] != self.timestamps.shape[0]:
            raise ValueError(
                f"data sample count {self.data.shape[1]} != "
                f"timestamps length {self.timestamps.shape[0]}"
            )


class FeatureVector(BaseModel):
    """Feature vector extracted from a SampleChunk."""
    
    stream: Dict[str, Any]  # StreamMeta as dict for JSON serialization
    t_start: float
    t_end: float
    features: Dict[str, Any]
    
    @classmethod
    def from_meta(cls, meta: StreamMeta, t_start: float, t_end: float, features: Dict[str, Any]) -> "FeatureVector":
        """Create from StreamMeta and feature dict."""
        return cls(
            stream=meta.to_dict(),
            t_start=t_start,
            t_end=t_end,
            features=features
        )
