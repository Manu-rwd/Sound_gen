"""Sample dispatcher for periodic broadcasting."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional

from ..config import config
from ..models.messages import SamplesMessage
from ..sensors.manager import SensorManager
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class SamplesDispatcher:
    """Periodically collects samples from sensors and broadcasts to clients.
    
    Runs at a configurable interval (default 20 Hz / 50ms) and:
    1. Drains sample buffers from all active sensors
    2. Packages samples into a SamplesMessage
    3. Broadcasts to all connected WebSocket clients
    """
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        sensor_manager: SensorManager,
        interval_sec: Optional[float] = None,
    ):
        """Initialize the dispatcher.
        
        Args:
            connection_manager: WebSocket connection manager for broadcasting.
            sensor_manager: Sensor manager to collect samples from.
            interval_sec: Dispatch interval in seconds. Defaults to config value.
        """
        self._conn_manager = connection_manager
        self._sensor_manager = sensor_manager
        self._interval = interval_sec or config.dispatcher_interval_sec
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    @property
    def running(self) -> bool:
        """Check if the dispatcher is running."""
        return self._running
    
    @property
    def interval_ms(self) -> float:
        """Get the dispatch interval in milliseconds."""
        return self._interval * 1000
    
    async def start(self) -> None:
        """Start the dispatcher loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"SamplesDispatcher started at {self.interval_ms:.0f}ms interval")
    
    async def stop(self) -> None:
        """Stop the dispatcher loop."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("SamplesDispatcher stopped")
    
    async def _loop(self) -> None:
        """Main dispatch loop."""
        try:
            while self._running:
                await self._dispatch()
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Dispatcher error: {e}")
            self._running = False
    
    async def _dispatch(self) -> None:
        """Collect and broadcast samples."""
        # Skip if no clients connected
        if self._conn_manager.client_count == 0:
            return
        
        # Drain samples from all sensors
        batches = self._sensor_manager.drain_all_samples()
        
        # Skip if no samples
        if not batches:
            return
        
        # Create and broadcast message
        message = SamplesMessage(
            type="samples",
            payload=batches,
        )
        
        await self._conn_manager.broadcast_json(message.model_dump())
