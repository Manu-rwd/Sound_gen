"""Tests for WebSocket basic functionality."""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from dashboard_backend.main import app


def test_health_endpoint():
    """Test the health check endpoint."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "clients" in data
        assert "dispatcher_running" in data


def test_sensors_endpoint():
    """Test the sensors list endpoint."""
    with TestClient(app) as client:
        response = client.get("/sensors")
        assert response.status_code == 200
        data = response.json()
        assert "sensors" in data
        assert isinstance(data["sensors"], list)
        # Should have 3 fake sensors
        assert len(data["sensors"]) == 3
        
        # Check sensor structure
        for sensor in data["sensors"]:
            assert "id" in sensor
            assert "name" in sensor
            assert "kind" in sensor
            assert "channels" in sensor
            assert "sampling_rate" in sensor


def test_websocket_connect_and_receive_descriptors():
    """Test WebSocket connection and initial descriptors message."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Should receive descriptors on connect
            data = websocket.receive_json()
            assert data["type"] == "descriptors"
            assert "payload" in data
            assert isinstance(data["payload"], list)
            assert len(data["payload"]) == 3  # 3 fake sensors


def test_websocket_ping_pong():
    """Test ping/pong for connection health."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Receive initial descriptors
            websocket.receive_json()
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"
            assert "timestamp" in data


def test_websocket_unknown_message_type():
    """Test error response for unknown message types."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Receive initial descriptors
            websocket.receive_json()
            
            # Send unknown message type
            websocket.send_json({"type": "unknown_type"})
            
            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "unknown_type" in data["message"].lower()


def test_websocket_enable_disable_device():
    """Test enabling and disabling a device via WebSocket."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Receive initial descriptors
            initial = websocket.receive_json()
            assert initial["type"] == "descriptors"
            
            # All devices should be disabled initially
            for sensor in initial["payload"]:
                assert sensor["enabled"] is False
            
            # Enable fake_eeg
            websocket.send_json({
                "type": "control",
                "action": "enable",
                "deviceId": "fake_eeg"
            })
            
            # Receive updated descriptors
            updated = websocket.receive_json()
            assert updated["type"] == "descriptors"
            
            # fake_eeg should now be enabled
            eeg_sensor = next(
                s for s in updated["payload"] if s["id"] == "fake_eeg"
            )
            assert eeg_sensor["enabled"] is True
            
            # Disable it
            websocket.send_json({
                "type": "control",
                "action": "disable",
                "deviceId": "fake_eeg"
            })
            
            # Receive updated descriptors
            disabled = websocket.receive_json()
            assert disabled["type"] == "descriptors"
            
            eeg_sensor = next(
                s for s in disabled["payload"] if s["id"] == "fake_eeg"
            )
            assert eeg_sensor["enabled"] is False
