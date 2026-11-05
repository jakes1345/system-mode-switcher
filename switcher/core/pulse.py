"""
Citadel Pulse Core — High-Performance Background Telemetry Engine.
Runs telemetry collection as a background 'pulse' to ensure zero lag in the UI.
"""

import logging
import threading
import time
from dataclasses import dataclass, field

import psutil

logger = logging.getLogger(__name__)



@dataclass
class TelemetryState:
    """Atomic state of the entire system's vitals."""
    cpu_heatmap: list[float] = field(default_factory=list)
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    gpu_temp: int = 0
    gpu_power: float = 0.0
    vram_used_mb: int = 0
    disk_iowait: float = 0.0
    last_update: float = 0.0

class PulseEngine:
    """Enterprise-grade background telemetry pulse."""
    
    def __init__(self, interval_ms: int = 500):
        self.interval = interval_ms / 1000.0
        self.state = TelemetryState()
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """Start the background pulse."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True, name="CitadelPulse")
            self._thread.start()

    def get_vitals(self) -> TelemetryState:
        """Thread-safe read of the last captured vitals."""
        with self._lock:
            return self.state

    def _run(self):
        """Main pulse loop."""
        import os
        # Set low priority for the telemetry thread to avoid interfering with gaming
        try:
            os.nice(10)
        except OSError:
            pass

        failing = False
        while self._running:
            start_loop = time.time()
            try:
                self._collect()
                failing = False
            except Exception:
                # The sampling thread must survive a bad sample. Log the first
                # failure of a run of failures rather than one per interval.
                if not failing:
                    logger.exception("Telemetry sample failed")
                failing = True
            
            elapsed = time.time() - start_loop
            sleep_time = max(0, self.interval - elapsed)
            time.sleep(sleep_time)

    def _collect(self):
        """Perform the actual hardware measurements."""
        # 1. CPU Heatmap (Per-core usage)
        core_percents = psutil.cpu_percent(interval=None, percpu=True)
        
        # 2. RAM Info
        mem = psutil.virtual_memory()
        
        # 3. Disk Pressure (I/O Wait)
        disk_v = psutil.cpu_times_percent(interval=None).iowait
        
        # Update State Atomically
        with self._lock:
            self.state.cpu_heatmap = core_percents
            self.state.ram_used_gb = round(mem.used / (1024**3), 2)
            self.state.ram_total_gb = round(mem.total / (1024**3), 1)
            self.state.disk_iowait = disk_v
            self.state.last_update = time.time()

# Singleton Pulse Instance
pulse = PulseEngine()
