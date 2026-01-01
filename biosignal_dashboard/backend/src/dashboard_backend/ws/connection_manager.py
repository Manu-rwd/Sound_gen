"""WebSocket connection manager."""

from __future__ import annotations
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts.
    
    Handles:
    - Connection registration and cleanup
    - Broadcasting messages to all connected clients
    - Per-client error handling (disconnect on error)
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to register.
        """
        await websocket.accept()
        self.active.append(websocket)
        logger.info(f"Client connected. Total clients: {len(self.active)}")
    
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the registry.
        
        Args:
            websocket: The WebSocket connection to remove.
        """
        if websocket in self.active:
            self.active.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.active)}")
    
    async def broadcast_json(self, data: dict) -> None:
        """Broadcast a JSON message to all connected clients.
        
        Clients that fail to receive the message are disconnected.
        
        Args:
            data: The JSON-serializable data to broadcast.
        """
        # Iterate over a copy to allow removal during iteration
        disconnected: List[WebSocket] = []
        
        for websocket in list(self.active):
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(websocket)
        
        # Clean up failed connections
        for ws in disconnected:
            self.disconnect(ws)
    
    async def send_to_client(self, websocket: WebSocket, data: dict) -> bool:
        """Send a JSON message to a specific client.
        
        Args:
            websocket: The target WebSocket connection.
            data: The JSON-serializable data to send.
            
        Returns:
            True if successful, False if the send failed.
        """
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client: {e}")
            self.disconnect(websocket)
            return False
    
    @property
    def client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self.active)
