"""Muse EEG source using LSL (BlueMuse backend)."""

from .base import EEGSource
from .lsl_client import discover_streams, select_streams_by_type, LSLStreamReader
from ..models import SampleChunk
from ..config import MUSE_EEG_TYPE


class MuseLSLEEGSource(EEGSource):
    """
    EEGSource implementation that reads Muse EEG from an existing LSL stream,
    typically produced by BlueMuse.
    """

    def __init__(self, name_filter: str | None = None):
        """
        Initialize the Muse LSL source.
        
        Args:
            name_filter: Optional substring to filter stream names (e.g., "Muse-1AE4")
                        If None, will match any stream containing "Muse"
        """
        self._name_filter = name_filter
        self._reader: LSLStreamReader | None = None

    def connect(self, wait_time: float = 5.0) -> None:
        """
        Discover LSL streams of type 'EEG', filter for names containing 'Muse'
        and optional name_filter substring, pick the first match and
        initialize LSLStreamReader.

        Args:
            wait_time: How long to wait for streams (seconds)
            
        Raises:
            RuntimeError: If no suitable Muse EEG stream is found
        """
        # Discover all streams
        all_streams = discover_streams(wait_time=wait_time)
        
        # Filter for EEG type
        eeg_streams = select_streams_by_type(all_streams, MUSE_EEG_TYPE)
        
        if not eeg_streams:
            raise RuntimeError(
                f"No LSL streams of type '{MUSE_EEG_TYPE}' found. "
                "Is BlueMuse streaming?"
            )
        
        # Filter for Muse devices
        muse_streams = [s for s in eeg_streams if "Muse" in s.name]
        
        if not muse_streams:
            raise RuntimeError(
                f"No Muse EEG streams found. Available EEG streams: "
                f"{[s.name for s in eeg_streams]}"
            )
        
        # Apply optional name filter
        if self._name_filter:
            filtered_streams = [
                s for s in muse_streams 
                if self._name_filter in s.name
            ]
            
            if not filtered_streams:
                raise RuntimeError(
                    f"No Muse streams matching filter '{self._name_filter}'. "
                    f"Available Muse streams: {[s.name for s in muse_streams]}"
                )
            
            selected_stream = filtered_streams[0]
        else:
            selected_stream = muse_streams[0]
        
        # Create and connect reader
        self._reader = LSLStreamReader(selected_stream)
        self._reader.connect(wait_time=wait_time)

    def read_chunk(self, max_samples: int, timeout: float = 1.0) -> SampleChunk | None:
        """
        Read a chunk of EEG samples.
        
        Args:
            max_samples: Maximum number of samples to read
            timeout: Timeout in seconds
            
        Returns:
            SampleChunk if data is available, None otherwise
            
        Raises:
            RuntimeError: If not connected
        """
        if self._reader is None:
            raise RuntimeError("MuseLSLEEGSource not connected. Call connect() first.")
        
        return self._reader.pull_chunk(max_samples=max_samples, timeout=timeout)
