"""Tests for SensorManager."""

import pytest
import asyncio

from dashboard_backend.sensors.manager import SensorManager
from dashboard_backend.models.descriptors import SensorDescriptor


def test_sensor_manager_init_fake_sensors():
    """Test SensorManager initializes with fake sensors."""
    manager = SensorManager(use_fake_sensors=True)
    
    descriptors = manager.descriptors()
    assert len(descriptors) == 3
    
    # Check all expected sensors are present
    ids = [d.id for d in descriptors]
    assert "fake_eeg" in ids
    assert "fake_gsr" in ids
    assert "fake_ecg" in ids


def test_sensor_manager_descriptors_structure():
    """Test sensor descriptors have correct structure."""
    manager = SensorManager(use_fake_sensors=True)
    
    for desc in manager.descriptors():
        assert isinstance(desc, SensorDescriptor)
        assert desc.id
        assert desc.name
        assert desc.kind in ["EEG", "ECG", "GSR", "HR", "ACCEL", "OTHER"]
        assert len(desc.channels) > 0
        assert desc.sampling_rate > 0


def test_sensor_manager_get_descriptor():
    """Test getting a specific descriptor."""
    manager = SensorManager(use_fake_sensors=True)
    
    desc = manager.get_descriptor("fake_eeg")
    assert desc is not None
    assert desc.id == "fake_eeg"
    assert desc.kind == "EEG"
    
    # Non-existent device
    assert manager.get_descriptor("nonexistent") is None


@pytest.mark.asyncio
async def test_sensor_manager_enable_disable():
    """Test enabling and disabling sensors."""
    manager = SensorManager(use_fake_sensors=True)
    
    # Initially disabled
    assert not manager.is_enabled("fake_eeg")
    
    # Enable
    success = await manager.enable("fake_eeg")
    assert success
    assert manager.is_enabled("fake_eeg")
    
    # Disable
    success = await manager.disable("fake_eeg")
    assert success
    assert not manager.is_enabled("fake_eeg")


@pytest.mark.asyncio
async def test_sensor_manager_enable_nonexistent():
    """Test enabling a non-existent device returns False."""
    manager = SensorManager(use_fake_sensors=True)
    
    success = await manager.enable("nonexistent")
    assert success is False


@pytest.mark.asyncio
async def test_sensor_manager_disable_all():
    """Test disabling all sensors."""
    manager = SensorManager(use_fake_sensors=True)
    
    # Enable all
    await manager.enable("fake_eeg")
    await manager.enable("fake_gsr")
    await manager.enable("fake_ecg")
    
    assert manager.is_enabled("fake_eeg")
    assert manager.is_enabled("fake_gsr")
    assert manager.is_enabled("fake_ecg")
    
    # Disable all
    await manager.disable_all()
    
    assert not manager.is_enabled("fake_eeg")
    assert not manager.is_enabled("fake_gsr")
    assert not manager.is_enabled("fake_ecg")


@pytest.mark.asyncio
async def test_sensor_manager_drain_samples():
    """Test draining samples from active sensors."""
    manager = SensorManager(use_fake_sensors=True)
    
    # No samples when disabled
    batches = manager.drain_all_samples()
    assert len(batches) == 0
    
    # Enable and let it run briefly
    await manager.enable("fake_eeg")
    await asyncio.sleep(0.2)  # Let fake sensor generate data
    
    # Should have samples now
    batches = manager.drain_all_samples()
    assert len(batches) == 1
    assert batches[0].deviceId == "fake_eeg"
    assert len(batches[0].values) > 0
    
    # Clean up
    await manager.disable_all()
