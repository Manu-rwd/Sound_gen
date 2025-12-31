"""Tests for Muse BrainFlow source."""

import pytest
from sound_gen_hub.acquisition.muse_brainflow import MuseBrainFlowSource
from sound_gen_hub.models import StreamMeta, SampleChunk
import numpy as np


class FakeBrainFlowMuseClient:
    """Fake BrainFlowMuseClient for testing."""
    
    def __init__(self, mac_address=None):
        self.mac_address = mac_address
        self.prepared = False
        self.streaming = False
        self.meta = None
        self._sample_num = 0
    
    def prepare_session(self):
        """Fake prepare session."""
        self.prepared = True
        self.meta = StreamMeta(
            name="Muse-2-BrainFlow-Test",
            type="EEG",
            channel_count=4,
            nominal_srate=256.0,
            source_id="fake-brainflow"
        )
    
    def start_stream(self, buffer_size):
        """Fake start stream."""
        if not self.prepared:
            raise RuntimeError("Not prepared")
        self.streaming = True
    
    def stop_and_release(self):
        """Fake stop and release."""
        self.streaming = False
        self.prepared = False
    
    def pull_chunk(self, max_samples):
        """Return fake chunk."""
        if not self.streaming:
            raise RuntimeError("Not streaming")
        
        n_samples = min(max_samples, 10)
        data = np.random.randn(4, n_samples)
        timestamps = np.arange(
            self._sample_num,
            self._sample_num + n_samples
        ) * (1.0 / 256.0)
        self._sample_num += n_samples
        
        return SampleChunk(
            meta=self.meta,
            timestamps=timestamps,
            data=data
        )


def test_muse_brainflow_source_connect():
    """Test connecting BrainFlow source."""
    fake_client = FakeBrainFlowMuseClient()
    source = MuseBrainFlowSource(client=fake_client)
    
    source.connect()
    
    assert fake_client.prepared
    assert fake_client.streaming


def test_muse_brainflow_source_read_chunk():
    """Test reading chunks."""
    fake_client = FakeBrainFlowMuseClient()
    source = MuseBrainFlowSource(client=fake_client)
    
    source.connect()
    
    chunk = source.read_chunk(max_samples=8)
    
    assert chunk is not None
    assert chunk.data.shape[0] == 4
    assert chunk.data.shape[1] > 0
    assert chunk.timestamps.shape[0] == chunk.data.shape[1]


def test_muse_brainflow_source_close():
    """Test closing the source."""
    fake_client = FakeBrainFlowMuseClient()
    source = MuseBrainFlowSource(client=fake_client)
    
    source.connect()
    assert fake_client.streaming
    
    source.close()
    
    assert not fake_client.streaming
    assert not fake_client.prepared


def test_muse_brainflow_source_with_mac():
    """Test initialization with MAC address."""
    fake_client = FakeBrainFlowMuseClient(mac_address="00:11:22:33:44:55")
    source = MuseBrainFlowSource(
        mac_address="00:11:22:33:44:55",
        client=fake_client
    )
    
    assert source._mac_address == "00:11:22:33:44:55"
    assert fake_client.mac_address == "00:11:22:33:44:55"


def test_muse_brainflow_source_multiple_reads():
    """Test reading multiple chunks."""
    fake_client = FakeBrainFlowMuseClient()
    source = MuseBrainFlowSource(client=fake_client)
    
    source.connect()
    
    chunk1 = source.read_chunk(max_samples=16)
    chunk2 = source.read_chunk(max_samples=16)
    
    assert chunk1 is not None
    assert chunk2 is not None
    
    # Timestamps should be increasing
    assert chunk2.timestamps[0] > chunk1.timestamps[-1]
