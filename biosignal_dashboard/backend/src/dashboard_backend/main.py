"""FastAPI application for the biosignal dashboard backend."""

from __future__ import annotations
import os
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .models.messages import (
    DescriptorsMessage,
    AudioEvent,
    AudioMessage,
    ErrorMessage,
    StateEstimate,
)
from .sensors.manager import SensorManager, SensorConfig
from .ws.connection_manager import ConnectionManager
from .ws.dispatcher import SamplesDispatcher
from .state.estimator import StateEstimator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Temporarily set to DEBUG to diagnose state estimation
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting biosignal dashboard backend...")
    
    # Check environment for sensor configuration
    use_real_sensors = os.environ.get("USE_REAL_SENSORS", "").lower() in ("1", "true", "yes")
    
    if use_real_sensors:
        # Configure real sensors
        sensor_config = SensorConfig(
            use_muse_eeg=True,
            muse_backend="brainflow",  # Direct Bluetooth, no BlueMuse needed
            muse_mac_address=os.environ.get("MUSE_MAC_ADDRESS"),
            use_gsr=bool(os.environ.get("GSR_PORT")),
            gsr_port=os.environ.get("GSR_PORT"),
            use_ecg=bool(os.environ.get("ECG_PORT")),
            ecg_port=os.environ.get("ECG_PORT"),
        )
        app.state.sensor_manager = SensorManager(
            use_fake_sensors=False,
            config=sensor_config,
        )
        logger.info("Using REAL sensors (BrainFlow for EEG)")
    else:
        # Use fake sensors for testing
        app.state.sensor_manager = SensorManager(use_fake_sensors=True)
        logger.info("Using FAKE sensors for testing")
    
    app.state.conn_manager = ConnectionManager()
    app.state.dispatcher = SamplesDispatcher(
        connection_manager=app.state.conn_manager,
        sensor_manager=app.state.sensor_manager,
    )
    
    # Create state estimator
    app.state.state_estimator = StateEstimator(
        update_interval=1.0,  # 1 Hz state updates
    )
    
    # Register state update callback to broadcast to clients
    def broadcast_state(state: StateEstimate):
        import asyncio
        asyncio.create_task(
            app.state.conn_manager.broadcast_json(state.model_dump())
        )
    app.state.state_estimator.register_callback(broadcast_state)
    
    # Connect dispatcher to feed data to state estimator
    app.state.dispatcher.set_state_estimator(app.state.state_estimator)
    
    # Start dispatcher and state estimator
    await app.state.dispatcher.start()
    await app.state.state_estimator.start()
    
    logger.info("Backend ready")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down...")
    await app.state.state_estimator.stop()
    await app.state.dispatcher.stop()
    await app.state.sensor_manager.disable_all()
    logger.info("Backend stopped")


# Create FastAPI app
app = FastAPI(
    title="Biosignal Dashboard Backend",
    description="Real-time biosignal streaming via WebSockets",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "clients": app.state.conn_manager.client_count,
        "dispatcher_running": app.state.dispatcher.running,
    }


@app.get("/sensors")
async def list_sensors():
    """List all available sensors."""
    sensors: SensorManager = app.state.sensor_manager
    return {
        "sensors": [desc.model_dump() for desc in sensors.descriptors()]
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming."""
    conn_manager: ConnectionManager = app.state.conn_manager
    sensor_manager: SensorManager = app.state.sensor_manager
    
    await conn_manager.connect(websocket)
    
    # Send initial sensor descriptors
    descriptors = [desc.model_dump() for desc in sensor_manager.descriptors()]
    await websocket.send_json(
        DescriptorsMessage(type="descriptors", payload=descriptors).model_dump()
    )
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            msg_type = data.get("type")
            
            if msg_type == "control":
                await handle_control_message(data, sensor_manager, conn_manager)
            
            elif msg_type == "audio_event":
                await handle_audio_event(data, conn_manager)
            
            elif msg_type == "ping":
                # Simple ping/pong for connection health
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
            
            else:
                # Unknown message type
                await websocket.send_json(
                    ErrorMessage(
                        type="error",
                        message=f"Unknown message type: {msg_type}"
                    ).model_dump()
                )
    
    except WebSocketDisconnect:
        conn_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        conn_manager.disconnect(websocket)


async def handle_control_message(
    data: dict,
    sensor_manager: SensorManager,
    conn_manager: ConnectionManager,
) -> None:
    """Handle device enable/disable control messages."""
    action = data.get("action")
    device_id = data.get("deviceId")
    
    if not device_id:
        return
    
    if action == "enable":
        success = await sensor_manager.enable(device_id)
        logger.info(f"Enabled device {device_id}: {success}")
    elif action == "disable":
        success = await sensor_manager.disable(device_id)
        logger.info(f"Disabled device {device_id}: {success}")
    else:
        return
    
    # Broadcast updated descriptors to all clients
    descriptors = [desc.model_dump() for desc in sensor_manager.descriptors()]
    await conn_manager.broadcast_json(
        DescriptorsMessage(type="descriptors", payload=descriptors).model_dump()
    )


async def handle_audio_event(
    data: dict,
    conn_manager: ConnectionManager,
) -> None:
    """Handle audio event messages and rebroadcast."""
    event = AudioEvent(
        timestamp=time.time(),
        event=data.get("event", "tag"),
        trackId=data.get("trackId"),
        trackName=data.get("trackName"),
        tags=data.get("tags"),
    )
    
    message = AudioMessage(type="audio", payload=event)
    await conn_manager.broadcast_json(message.model_dump())


def run_server():
    """Run the server with uvicorn."""
    import uvicorn
    uvicorn.run(
        "dashboard_backend.main:app",
        host=config.host,
        port=config.port,
        reload=True,
    )


if __name__ == "__main__":
    run_server()
