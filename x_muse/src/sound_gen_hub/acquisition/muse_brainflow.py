"""Muse EEG source using BrainFlow (native BLE backend)."""

from .base import EEGSource
from .brainflow_client import BrainFlowMuseClient
from ..models import SampleChunk


class MuseBrainFlowSource(EEGSource):
    """
    EEGSource implementation using BrainFlow's Muse 2 native BLE backend.
    """

    def __init__(
        self,
        mac_address: str | None = None,
        buffer_size: int = 45000,
        client: BrainFlowMuseClient | None = None,
    ):
        """
        Initialize Muse BrainFlow source.
        
        Args:
            mac_address: Optional MAC address for the Muse device
            buffer_size: Internal buffer size for BrainFlow
            client: Optional BrainFlowMuseClient instance (for testing)
        """
        self._mac_address = mac_address
        self._buffer_size = buffer_size
        self._client = client or BrainFlowMuseClient(mac_address=mac_address)

    def connect(self) -> None:
        """
        Prepare the BrainFlow session and start streaming.
        
        Raises:
            RuntimeError: If connection fails
        """
        self._client.prepare_session()
        self._client.start_stream(self._buffer_size)

    def read_chunk(self, max_samples: int, timeout: float = 1.0) -> SampleChunk | None:
        """
        Read a chunk of EEG samples.
        
        Note: BrainFlow buffers data internally, so timeout is not used.
        
        Args:
            max_samples: Maximum number of samples to read
            timeout: Timeout in seconds (ignored for BrainFlow)
            
        Returns:
            SampleChunk if data is available, None otherwise
        """
        return self._client.pull_chunk(max_samples=max_samples)

    def close(self) -> None:
        """Stop streaming and release the session."""
        self._client.stop_and_release()
