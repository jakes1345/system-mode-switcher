"""
Citadel Vector — Zero-Copy Shared Memory Telemetry IPC.
The 'Google-Grade' way to pass telemetry between processes without CPU cost.
"""

import mmap
import struct
import os
from typing import List

# Format: [Timestamp(d), CPU_Count(I), Heatmap[64](f), RAM_Used(d), GPU_Temp(I)]
# Roughly 300 bytes per snapshot
SHM_SIZE = 1024
SHM_NAME = "/dev/shm/citadel_vector"

class CitadelVector:
    def __init__(self, provider=False):
        self.provider = provider
        self.fd = -1
        self.mm = None
        try:
            if provider:
                # Create shared memory file in /dev/shm
                self.fd = os.open(SHM_NAME, os.O_CREAT | os.O_RDWR, 0o666)
                os.write(self.fd, b'\x00' * SHM_SIZE)
            else:
                self.fd = os.open(SHM_NAME, os.O_RDONLY)
                
            self.mm = mmap.mmap(self.fd, SHM_SIZE)
        except (FileNotFoundError, OSError):
            self.mm = None

    def write_vitals(self, heatmap: List[float], ram_used: float):
        """Write current stats to SHM in binary format (Zero Copy)."""
        if not self.provider or not self.mm: return
        
        # Pack precisely (d=double, I=unsigned int, f=float)
        # We cap at 16 cores for this demo
        flat_map = heatmap[:16] + [0.0] * (16 - len(heatmap))
        data = struct.pack('dI16f d', 
                           os.times().elapsed, 
                           len(heatmap),
                           *flat_map,
                           ram_used)
        
        self.mm.seek(0)
        self.mm.write(data)

    def read_vitals(self) -> dict:
        """Read the absolute latest vitals with zero overhead."""
        if not self.mm:
            return {"elapsed": 0.0, "cores": 0, "heatmap": [], "ram_gb": 0.0}
        self.mm.seek(0)
        struct_fmt = 'dI16f d'
        size = struct.calcsize(struct_fmt)
        buf = self.mm.read(size) # Read exact struct size
        res = struct.unpack(struct_fmt, buf)
        
        return {
            "elapsed": res[0],
            "cores": res[1],
            "heatmap": list(res[2:18])[:res[1]],
            "ram_gb": res[18]
        }

    def close(self):
        self.mm.close()
        os.close(self.fd)
        if self.provider:
            try:
                os.unlink(SHM_NAME)
            except OSError:
                pass
