"""Multiplexer for sharing a single Teensy serial connection between multiple sensors."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Set
import serial
from serial.tools import list_ports

logger = logging.getLogger(__name__)

class TeensyMultiplexer:
    """
    Manages a single serial connection to a multi-sensor Teensy.
    Parses lines and dispatches them to registered callbacks based on label.
    """
    
    _instances: Dict[str, 'TeensyMultiplexer'] = {}
    
    @classmethod
    def get_instance(cls, port: str) -> 'TeensyMultiplexer':
        """Get or create singleton instance for a specific port."""
        if port not in cls._instances:
            cls._instances[port] = cls(port)
        return cls._instances[port]
    
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._serial: Optional[serial.Serial] = None
        self._running = False
        self._callbacks: Dict[str, List[Callable[[float, float, float], None]]] = {
            "GSR": [],
            "ECG": []
        }
        self._lock = asyncio.Lock()
        
    def register_callback(self, label: str, callback: Callable[[float, float, float], None]):
        """
        Register a callback for a specific sensor label (GSR or ECG).
        Callback signature: (timestamp, value, extra_info)
        """
        if label not in self._callbacks:
            self._callbacks[label] = []
        self._callbacks[label].append(callback)
        
    async def start(self):
        """Start the read loop if not running."""
        if self._running:
            return
            
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._connect)
            self._running = True
            asyncio.create_task(self._read_loop())
            logger.info(f"TeensyMultiplexer started on {self.port}")
        except Exception as e:
            logger.error(f"Failed to start TeensyMultiplexer: {e}")
            raise

    def _connect(self):
        """Blocking connect."""
        if self._serial and self._serial.is_open:
            return
        
        logger.info(f"Opening shared serial port {self.port} at {self.baudrate}")
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=1.0)
            time.sleep(0.5) # Reset wait
            self._serial.reset_input_buffer()
            logger.info("Serial port opened successfully")
        except Exception as e:
            logger.error(f"Error opening serial port: {e}")
            raise

    async def _read_loop(self):
        """Async read loop."""
        loop = asyncio.get_running_loop()
        logger.info("Starting read loop")
        while self._running:
            try:
                if self._serial and self._serial.in_waiting:
                    # Read line in thread to avoid blocking loop
                    line = await loop.run_in_executor(None, self._serial.readline)
                    if line:
                        logger.debug(f"RAW LINE: {line}")
                        self._process_line(line)
                else:
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Teensy read error: {e}")
                await asyncio.sleep(1)

    def _process_line(self, line_bytes: bytes):
        """Parse line and dispatch."""
        try:
            line = line_bytes.decode('ascii', errors='ignore').strip()
            if not line:
                return
            
            # logger.debug(f"Processing line: {line}")
            parts = line.split(',')
            # Expected formats:
            # millis, LABEL, value, [status]
            
            if len(parts) >= 3:
                # Standard format
                millis = int(parts[0])
                label = parts[1].upper()
                value = float(parts[2])
                
                if label in self._callbacks:
                    timestamp = time.time()
                    count = len(self._callbacks[label])
                    # logger.debug(f"Dispatching {label} value {value} to {count} callbacks")
                    for cb in self._callbacks[label]:
                        cb(timestamp, value)
            else:
                 logger.debug(f"Ignored line (format mismatch): {line}")

        except ValueError:
             logger.warning(f"Malformed line: {line}")
        except Exception as e:
            logger.warning(f"Parse error: {e}")

    async def stop(self):
        """Stop reading."""
        self._running = False
        if self._serial:
            self._serial.close()
