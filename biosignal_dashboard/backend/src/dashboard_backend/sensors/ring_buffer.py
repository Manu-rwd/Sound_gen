"""Thread-safe ring buffer for sensor samples."""

from __future__ import annotations
import threading
from typing import List, Tuple, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class BufferEntry:
    """A single entry in the ring buffer."""
    timestamp: float
    data: np.ndarray  # shape varies by sensor


class RingBuffer:
    """Thread-safe ring buffer for storing timestamped sample chunks.
    
    Designed for producer-consumer pattern where sensor runners
    push data and the dispatcher drains it periodically.
    """
    
    def __init__(self, maxlen: int = 4096):
        """Initialize the ring buffer.
        
        Args:
            maxlen: Maximum number of entries to store.
                   Older entries are discarded when full.
        """
        self._maxlen = maxlen
        self._buffer: List[BufferEntry] = []
        self._lock = threading.Lock()
    
    def append(self, timestamp: float, data: np.ndarray) -> None:
        """Append a new entry to the buffer.
        
        Args:
            timestamp: Unix timestamp for the data chunk.
            data: Numpy array of sample data.
        """
        with self._lock:
            self._buffer.append(BufferEntry(timestamp=timestamp, data=data))
            # Trim if over capacity
            if len(self._buffer) > self._maxlen:
                self._buffer = self._buffer[-self._maxlen:]
    
    def consume_all(self) -> Tuple[List[float], List[np.ndarray]]:
        """Consume and return all entries in the buffer.
        
        Returns:
            Tuple of (timestamps, data_chunks) where:
            - timestamps: List of Unix timestamps
            - data_chunks: List of numpy arrays
        
        After this call, the buffer is empty.
        """
        with self._lock:
            if not self._buffer:
                return [], []
            
            timestamps = [entry.timestamp for entry in self._buffer]
            data_chunks = [entry.data for entry in self._buffer]
            self._buffer.clear()
            return timestamps, data_chunks
    
    def is_empty(self) -> bool:
        """Check if the buffer is empty."""
        with self._lock:
            return len(self._buffer) == 0
    
    def __len__(self) -> int:
        """Return the number of entries in the buffer."""
        with self._lock:
            return len(self._buffer)
