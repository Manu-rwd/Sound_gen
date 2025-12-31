"""Tests for BrainFlow client wrapper."""

import numpy as np
import pytest
from sound_gen_hub.acquisition.brainflow_client import BrainFlowMuseClient


class FakeBoardShim:
    """Fake BoardShim for testing without real hardware."""
    
    def __init__(self, board_id, params):
        self.board_id = board_id
        self.params = params
        self._prepared = False
        self._streaming = False
        self._sample_counter = 0
        
    def prepare_session(self):
        """Fake prepare session."""
        self._prepared = True
    
    def is_prepared(self):
        """Check if session is prepared."""
        return self._prepared
    
    def start_stream(self, buffer_size):
        """Fake start stream."""
        if not self._prepared:
            raise RuntimeError("Session not prepared")
        self._streaming = True
    
    def stop_stream(self):
        """Fake stop stream."""
        self._streaming = False
    
    def release_session(self):
        """Fake release session."""
        self._prepared = False
    
    def get_current_board_data(self, max_samples):
        """
        Return fake board data.
        
        Returns array with shape (n_rows, n_samples) where:
        - Rows 0-3: EEG channels
        - Row 22: Timestamp channel (for Muse 2)
        """
        if not self._streaming:
            return np.array([]).reshape(23, 0)
        
        # Generate some fake samples
        n_samples = min(max_samples, 10)
        
        # Create data array (23 rows for Muse 2 board format)
        data = np.zeros((23, n_samples))
        
        # Fill EEG channels (0-3 for Muse 2)
        for ch in range(4):
            data[ch, :] = np.random.randn(n_samples) * 10 + ch * 100
        
        # Fill timestamp channel (22 for Muse 2)
        for i in range(n_samples):
            data[22, i] = self._sample_counter * 0.00390625  # ~256 Hz
            self._sample_counter += 1
        
        return data


def make_fake_board_factory():
    """Create a factory function that returns FakeBoardShim."""
    def factory(board_id, params):
        return FakeBoardShim(board_id, params)
    return factory


# Mock the BoardShim static methods
def mock_get_eeg_channels(board_id):
    """Mock get_eeg_channels."""
    return [0, 1, 2, 3]


def mock_get_sampling_rate(board_id):
    """Mock get_sampling_rate."""
    return 256


def mock_get_timestamp_channel(board_id):
    """Mock get_timestamp_channel."""
    return 22


def test_brainflow_client_prepare_session(monkeypatch):
    """Test preparing BrainFlow session."""
    # Mock the static methods
    from brainflow import BoardShim
    monkeypatch.setattr(BoardShim, 'get_eeg_channels', mock_get_eeg_channels)
    monkeypatch.setattr(BoardShim, 'get_sampling_rate', mock_get_sampling_rate)
    
    client = BrainFlowMuseClient(
        mac_address=None,
        board_factory=make_fake_board_factory()
    )
    
    client.prepare_session()
    
    # Check metadata was created
    meta = client.meta
    assert meta.name == "Muse-2-BrainFlow"
    assert meta.type == "EEG"
    assert meta.channel_count == 4
    assert meta.nominal_srate == 256.0
    assert meta.source_id == "brainflow"


def test_brainflow_client_start_stream(monkeypatch):
    """Test starting the stream."""
    from brainflow import BoardShim
    monkeypatch.setattr(BoardShim, 'get_eeg_channels', mock_get_eeg_channels)
    monkeypatch.setattr(BoardShim, 'get_sampling_rate', mock_get_sampling_rate)
    
    client = BrainFlowMuseClient(board_factory=make_fake_board_factory())
    client.prepare_session()
    client.start_stream(buffer_size=1000)
    
    # Should not raise


def test_brainflow_client_pull_chunk(monkeypatch):
    """Test pulling data chunks."""
    from brainflow import BoardShim
    monkeypatch.setattr(BoardShim, 'get_eeg_channels', mock_get_eeg_channels)
    monkeypatch.setattr(BoardShim, 'get_sampling_rate', mock_get_sampling_rate)
    monkeypatch.setattr(BoardShim, 'get_timestamp_channel', mock_get_timestamp_channel)
    
    client = BrainFlowMuseClient(board_factory=make_fake_board_factory())
    client.prepare_session()
    client.start_stream()
    
    chunk = client.pull_chunk(max_samples=16)
    
    assert chunk is not None
    assert chunk.data.shape[0] == 4  # 4 EEG channels
    assert chunk.data.shape[1] > 0  # At least some samples
    assert chunk.timestamps.shape[0] == chunk.data.shape[1]
    assert chunk.meta.name == "Muse-2-BrainFlow"


def test_brainflow_client_not_prepared():
    """Test errors when session not prepared."""
    client = BrainFlowMuseClient(board_factory=make_fake_board_factory())
    
    with pytest.raises(RuntimeError, match="Session not prepared"):
        client.start_stream()
    
    with pytest.raises(RuntimeError, match="Session not prepared"):
        _ = client.meta


def test_brainflow_client_not_started(monkeypatch):
    """Test errors when stream not started."""
    from brainflow import BoardShim
    monkeypatch.setattr(BoardShim, 'get_eeg_channels', mock_get_eeg_channels)
    monkeypatch.setattr(BoardShim, 'get_sampling_rate', mock_get_sampling_rate)
    
    client = BrainFlowMuseClient(board_factory=make_fake_board_factory())
    client.prepare_session()
    
    # Don't start stream
    with pytest.raises(RuntimeError, match="Stream not started"):
        client.pull_chunk(max_samples=16)


def test_brainflow_client_stop_and_release(monkeypatch):
    """Test cleanup."""
    from brainflow import BoardShim
    monkeypatch.setattr(BoardShim, 'get_eeg_channels', mock_get_eeg_channels)
    monkeypatch.setattr(BoardShim, 'get_sampling_rate', mock_get_sampling_rate)
    
    client = BrainFlowMuseClient(board_factory=make_fake_board_factory())
    client.prepare_session()
    client.start_stream()
    
    client.stop_and_release()
    
    # Should be able to call multiple times without error
    client.stop_and_release()
