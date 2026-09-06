"""
Citadel Observability Suite — Structured Logging and Telemetry Events.
Optimized for high-performance dashboard feedback and audit trails.
"""

import json
import logging
import os
import threading
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

class CitadelLogger:
    """Thread-safe enterprise logger with rotation and event stream support."""

    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            # Always log to the project directory for consistency —
            # /var/log/citadel doesn't exist and the root service can't
            # create it under ProtectSystem restrictions.
            log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        self.log_dir = log_dir
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        
        self.log_file = self.log_dir / "citadel.log"
        self.telemetry_log = self.log_dir / "telemetry_events.jsonl"
        
        self._lock = threading.Lock()
        
        # 1. Human-Readable System Log
        self._logger = logging.getLogger("ObsidianCitadel")
        self._logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
        try:
            handler = RotatingFileHandler(self.log_file, maxBytes=5*1024*1024, backupCount=3)
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        except (PermissionError, OSError):
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        
        # 2. Add stderr for debugging/containers (only if CITADEL_DEBUG is set)
        if os.environ.get("CITADEL_DEBUG", "").lower() in ("1", "true", "yes"):
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            self._logger.addHandler(console)

    def log(self, level: str, module: str, message: str, **extra):
        """Write a structured event to log and telemetry stream."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "module": module,
            "message": message,
            **extra
        }

        with self._lock:
            try:
                with open(self.telemetry_log, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except (OSError, TypeError):
                pass

            lvl_num = getattr(logging, level.upper(), logging.INFO)
            self._logger.log(lvl_num, f"[{module}] {message}")

    def info(self, module: str, message: str, **extra): self.log("INFO", module, message, **extra)
    def warn(self, module: str, message: str, **extra): self.log("WARNING", module, message, **extra)
    def error(self, module: str, message: str, **extra): self.log("ERROR", module, message, **extra)
    def debug(self, module: str, message: str, **extra): self.log("DEBUG", module, message, **extra)

# Singleton Instance
logger = CitadelLogger()
