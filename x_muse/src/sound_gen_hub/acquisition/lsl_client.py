"""LSL client utilities for discovering and reading streams."""

from pylsl import StreamInlet, StreamInfo, resolve_streams
import numpy as np
from ..models import StreamMeta, SampleChunk


def discover_streams(wait_time: float = 5.0) -> list[StreamMeta]:
    """
    Discover all LSL streams on the network.
    
    Args:
        wait_time: How long to wait for streams (seconds)
        
    Returns:
        List of StreamMeta for all discovered streams
    """
    infos = resolve_streams(wait_time=wait_time)
    return [_info_to_meta(info) for info in infos]


def select_streams_by_type(streams: list[StreamMeta], desired_type: str) -> list[StreamMeta]:
    """
    Filter streams by type.
    
    Args:
        streams: List of StreamMeta objects
        desired_type: Stream type to filter for (e.g., "EEG")
        
    Returns:
        Filtered list of streams matching the desired type
    """
    return [s for s in streams if s.type == desired_type]


def _info_to_meta(info: StreamInfo) -> StreamMeta:
    """Convert LSL StreamInfo to StreamMeta."""
    return StreamMeta(
        name=info.name(),
        type=info.type(),
        channel_count=info.channel_count(),
        nominal_srate=info.nominal_srate(),
        source_id=info.source_id() if info.source_id() else None
    )


class LSLStreamReader:
    """Reads samples from an LSL stream."""
    
    def __init__(self, meta: StreamMeta):
        """
        Initialize reader with stream metadata.
        
        Args:
            meta: StreamMeta describing the stream to connect to
        """
        self._meta = meta
        self._inlet: StreamInlet | None = None

    def connect(self, wait_time: float = 5.0) -> None:
        """
        Resolve the underlying LSL StreamInfo and create a StreamInlet.
        
        Args:
            wait_time: How long to wait for the stream
            
        Raises:
            RuntimeError: If stream cannot be found
        """
        # Resolve streams and find matching one
        infos = resolve_streams(wait_time=wait_time)
        
        matching_info = None
        for info in infos:
            if (info.name() == self._meta.name and 
                info.type() == self._meta.type):
                matching_info = info
                break
        
        if matching_info is None:
            raise RuntimeError(
                f"Could not find LSL stream: name={self._meta.name}, "
                f"type={self._meta.type}"
            )
        
        self._inlet = StreamInlet(matching_info, max_buflen=60)

    def pull_chunk(self, max_samples: int, timeout: float = 1.0) -> SampleChunk | None:
        """
        Pull a chunk of samples from the stream.
        
        Args:
            max_samples: Maximum number of samples to retrieve
            timeout: Timeout in seconds
            
        Returns:
            SampleChunk if data is available, None otherwise
            
        Raises:
            RuntimeError: If not connected
        """
        if self._inlet is None:
            raise RuntimeError("LSLStreamReader not connected.")
        
        # Pull chunk from inlet
        samples, timestamps = self._inlet.pull_chunk(
            timeout=timeout,
            max_samples=max_samples
        )
        
        if not samples:
            return None
        
        # Convert to numpy arrays with proper shape
        # samples is list of lists: [[ch0, ch1, ...], [ch0, ch1, ...], ...]
        # We need shape (n_channels, n_samples)
        data = np.array(samples).T  # Transpose to get (channels, samples)
        timestamps_arr = np.array(timestamps)
        
        return SampleChunk(
            meta=self._meta,
            timestamps=timestamps_arr,
            data=data
        )
