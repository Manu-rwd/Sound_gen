"""Configuration settings for the dashboard backend."""

from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""
    
    # WebSocket dispatcher settings
    dispatcher_interval_ms: int = 50  # Default 20 Hz, adjustable 25-100ms
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Sensor buffer settings
    buffer_max_samples: int = 4096
    
    @property
    def dispatcher_interval_sec(self) -> float:
        """Get dispatcher interval in seconds."""
        return self.dispatcher_interval_ms / 1000.0


# Global config instance
config = Config()
