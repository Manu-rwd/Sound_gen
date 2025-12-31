"""Base interface for EEG data sources."""

from abc import ABC, abstractmethod
from ..models import SampleChunk


class EEGSource(ABC):
    """Common interface for EEG data sources."""

    @abstractmethod
    def connect(self) -> None:
        """Prepare underlying connection (LSL, BrainFlow, etc.)."""
        pass

    @abstractmethod
    def read_chunk(self, max_samples: int, timeout: float = 1.0) -> SampleChunk | None:
        """
        Return up to max_samples samples as SampleChunk.
        
        Args:
            max_samples: Maximum number of samples to read
            timeout: Timeout in seconds to wait for data
            
        Returns:
            SampleChunk if samples are available, None otherwise
        """
        pass
