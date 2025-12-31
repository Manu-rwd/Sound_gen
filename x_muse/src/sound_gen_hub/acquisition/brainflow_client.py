"""BrainFlow wrapper for Muse 2 EEG acquisition."""

from typing import Callable
import numpy as np
from brainflow import BoardShim, BrainFlowInputParams, BoardIds
from ..models import StreamMeta, SampleChunk


class BrainFlowMuseClient:
    """
    Thin wrapper around BrainFlow BoardShim for Muse 2.
    Allows dependency injection of a custom BoardShim factory for tests.
    """

    def __init__(
        self,
        mac_address: str | None = None,
        board_factory: Callable[[int, BrainFlowInputParams], BoardShim] | None = None,
    ):
        """
        Initialize BrainFlow client for Muse 2.
        
        Args:
            mac_address: Optional MAC address for the Muse device
            board_factory: Optional factory function for creating BoardShim (for testing)
        """
        self._mac_address = mac_address
        self._board_factory = board_factory or self._default_board_factory
        self._board: BoardShim | None = None
        self._meta: StreamMeta | None = None
        self._eeg_channels: list[int] = []
        self._streaming = False

    @staticmethod
    def _default_board_factory(board_id: int, params: BrainFlowInputParams) -> BoardShim:
        """Default factory for creating BoardShim."""
        return BoardShim(board_id, params)

    @property
    def meta(self) -> StreamMeta:
        """Get stream metadata."""
        if self._meta is None:
            raise RuntimeError("Session not prepared. Call prepare_session() first.")
        return self._meta

    def prepare_session(self) -> None:
        """
        Configure BrainFlowInputParams for Muse 2 and prepare the session.
        
        Raises:
            RuntimeError: If session preparation fails
        """
        # Configure parameters for Muse 2
        params = BrainFlowInputParams()
        if self._mac_address:
            params.mac_address = self._mac_address
        
        # Use Muse 2 board ID
        board_id = BoardIds.MUSE_2_BOARD.value
        
        # Create board instance
        self._board = self._board_factory(board_id, params)
        
        # Prepare session
        try:
            self._board.prepare_session()
        except Exception as e:
            raise RuntimeError(f"Failed to prepare BrainFlow session: {e}")
        
        # Get board description to build metadata
        self._eeg_channels = BoardShim.get_eeg_channels(board_id)
        sampling_rate = BoardShim.get_sampling_rate(board_id)
        
        self._meta = StreamMeta(
            name=f"Muse-2-BrainFlow",
            type="EEG",
            channel_count=len(self._eeg_channels),
            nominal_srate=float(sampling_rate),
            source_id="brainflow"
        )

    def start_stream(self, buffer_size: int = 45000) -> None:
        """
        Start the data stream.
        
        Args:
            buffer_size: Size of the internal buffer
            
        Raises:
            RuntimeError: If session not prepared or stream start fails
        """
        if self._board is None:
            raise RuntimeError("Session not prepared. Call prepare_session() first.")
        
        try:
            self._board.start_stream(buffer_size)
            self._streaming = True
        except Exception as e:
            raise RuntimeError(f"Failed to start stream: {e}")

    def stop_and_release(self) -> None:
        """Stop stream and release the session."""
        if self._board is not None:
            try:
                if self._board.is_prepared():
                    self._board.stop_stream()
                    self._board.release_session()
            except Exception:
                # Ignore errors during cleanup
                pass
            finally:
                self._board = None
                self._streaming = False

    def pull_chunk(self, max_samples: int) -> SampleChunk | None:
        """
        Pull a chunk of data from the board.
        
        Args:
            max_samples: Maximum number of samples to retrieve
            
        Returns:
            SampleChunk if data is available, None otherwise
            
        Raises:
            RuntimeError: If stream not started
        """
        if not self._streaming:
            raise RuntimeError("Stream not started. Call prepare_session() and start_stream() first.")
        
        # Get current board data
        try:
            data = self._board.get_current_board_data(max_samples)
        except Exception as e:
            raise RuntimeError(f"Failed to get board data: {e}")
        
        if data.size == 0:
            return None
        
        # Extract EEG channels
        eeg_data = data[self._eeg_channels, :]
        
        # Get timestamp channel
        timestamp_channel = BoardShim.get_timestamp_channel(BoardIds.MUSE_2_BOARD.value)
        timestamps = data[timestamp_channel, :]
        
        if eeg_data.shape[1] == 0:
            return None
        
        return SampleChunk(
            meta=self._meta,
            timestamps=timestamps,
            data=eeg_data
        )
