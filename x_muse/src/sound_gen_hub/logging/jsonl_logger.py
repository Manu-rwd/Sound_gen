"""JSONL session logger for EEG features."""

from pathlib import Path
from typing import TextIO, Any, Dict
from pydantic import BaseModel
import json
from ..models import FeatureVector


class SessionLogConfig(BaseModel):
    """Configuration for session logger."""
    
    output_path: Path
    append: bool = True


class JSONLSessionLogger:
    """Logger that writes feature vectors to JSONL files."""
    
    def __init__(self, config: SessionLogConfig):
        """
        Initialize logger with configuration.
        
        Args:
            config: SessionLogConfig with output path and options
        """
        self._config = config
        self._fh: TextIO | None = None

    def open(self) -> None:
        """
        Open the log file for writing.
        
        Creates parent directories if needed.
        """
        mode = "a" if self._config.append else "w"
        self._config.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self._config.output_path.open(mode, encoding="utf-8")

    def log_feature_vector(
        self,
        fv: FeatureVector,
        now_playing: str | None = None,
        extra: Dict[str, Any] | None = None,
    ) -> None:
        """
        Log a feature vector as a JSONL entry.
        
        Args:
            fv: FeatureVector to log
            now_playing: Optional string describing what's currently playing
            extra: Optional dict of extra metadata
            
        Raises:
            RuntimeError: If logger not opened
        """
        if self._fh is None:
            raise RuntimeError("Logger not opened. Call open() first.")

        payload = {
            "t_start": fv.t_start,
            "t_end": fv.t_end,
            "stream": fv.stream,
            "features": fv.features,
            "now_playing": now_playing,
            "extra": extra or {},
        }
        
        self._fh.write(json.dumps(payload) + "\n")
        self._fh.flush()

    def close(self) -> None:
        """Close the log file."""
        if self._fh is not None:
            self._fh.close()
            self._fh = None
