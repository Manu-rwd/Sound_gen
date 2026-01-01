"""Tests for FakeSensorRunner."""

import pytest
import asyncio
import numpy as np

from dashboard_backend.sensors.fake_runner import (
    FakeSensorRunner,
    create_fake_eeg_runner,
    create_fake_gsr_runner,
    create_fake_ecg_runner,
)
from dashboard_backend.models.descriptors import SensorDescriptor, ChannelInfo


def test_create_fake_eeg_runner():
    """Test creating a fake EEG runner."""
    runner = create_fake_eeg_runner()
    
    assert runner.descriptor.id == "fake_eeg"
    assert runner.descriptor.kind == "EEG"
    assert len(runner.descriptor.channels) == 4
    assert runner.descriptor.sampling_rate == 256.0


def test_create_fake_gsr_runner():
    """Test creating a fake GSR runner."""
    runner = create_fake_gsr_runner()
    
    assert runner.descriptor.id == "fake_gsr"
    assert runner.descriptor.kind == "GSR"
    assert len(runner.descriptor.channels) == 1
    assert runner.descriptor.sampling_rate == 50.0


def test_create_fake_ecg_runner():
    """Test creating a fake ECG runner."""
    runner = create_fake_ecg_runner()
    
    assert runner.descriptor.id == "fake_ecg"
    assert runner.descriptor.kind == "ECG"
    assert len(runner.descriptor.channels) == 1
    assert runner.descriptor.sampling_rate == 250.0


@pytest.mark.asyncio
async def test_fake_runner_start_stop():
    """Test starting and stopping the fake runner."""
    runner = create_fake_eeg_runner()
    
    assert not runner.running
    
    await runner.start()
    assert runner.running
    
    await runner.stop()
    assert not runner.running


@pytest.mark.asyncio
async def test_fake_runner_generates_data():
    """Test that fake runner generates sample data."""
    runner = create_fake_eeg_runner()
    
    await runner.start()
    
    # Let it run for a bit
    await asyncio.sleep(0.2)
    
    # Drain buffer
    batch = runner.drain_buffer()
    
    await runner.stop()
    
    # Should have data
    assert batch is not None
    assert batch.deviceId == "fake_eeg"
    assert len(batch.values) > 0
    assert len(batch.channels) == 4


@pytest.mark.asyncio
async def test_fake_runner_data_shape():
    """Test that generated data has correct shape."""
    runner = create_fake_eeg_runner()
    
    await runner.start()
    await asyncio.sleep(0.15)
    
    batch = runner.drain_buffer()
    await runner.stop()
    
    assert batch is not None
    
    # Each value row should have 4 channels
    for row in batch.values:
        assert len(row) == 4


@pytest.mark.asyncio
async def test_fake_runner_single_channel():
    """Test fake runner with single channel (GSR-like)."""
    runner = create_fake_gsr_runner()
    
    await runner.start()
    await asyncio.sleep(0.2)
    
    batch = runner.drain_buffer()
    await runner.stop()
    
    assert batch is not None
    assert len(batch.channels) == 1
    
    # Each value row should have 1 channel
    for row in batch.values:
        assert len(row) == 1


@pytest.mark.asyncio
async def test_fake_runner_drain_clears_buffer():
    """Test that draining clears the buffer."""
    runner = create_fake_eeg_runner()
    
    await runner.start()
    await asyncio.sleep(0.15)
    
    # First drain gets data
    batch1 = runner.drain_buffer()
    assert batch1 is not None
    assert len(batch1.values) > 0
    
    # Immediate second drain should be empty (or have very few samples)
    batch2 = runner.drain_buffer()
    assert batch2 is None or len(batch2.values) < len(batch1.values)
    
    await runner.stop()
