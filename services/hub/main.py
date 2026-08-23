import sys
import os
import asyncio
import time
import grpc
from pathlib import Path

# Add the current directory to sys.path so it can find citadel_pb2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import citadel_pb2
import citadel_pb2_grpc

# Ensure project root is in path to import switcher module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from google.protobuf import timestamp_pb2
from switcher.backend import get_system_vitals_snapshot
from services.hub.reconciler import CitadelReconciler
from switcher.config import load_config

class CitadelController:
    """The 'Brain' — Reconciles Desired State vs Actual State."""
    def __init__(self):
        self.desired_profile = None  # No profile enforced until explicitly set via SetProfile
        self._lock = asyncio.Lock()
        
        # Load config and start reconciler
        self.config = load_config()
        self.reconciler = CitadelReconciler(self.config)
        self.reconciler.active_profile_name = self.desired_profile

class CitadelHubService(citadel_pb2_grpc.CitadelServiceServicer):
    """The gRPC Service implementation."""
    def __init__(self, controller: CitadelController):
        self.controller = controller

    async def SetProfile(self, request, context):
        async with self.controller._lock:
            self.controller.desired_profile = request.profile_name
            self.controller.reconciler.active_profile_name = request.profile_name
        
        resp = timestamp_pb2.Timestamp()
        resp.FromSeconds(int(time.time()))
        return citadel_pb2.ProfileResponse(
            success=True,
            message=f"Profile '{request.profile_name}' activated — reconciler enforcing state.",
            applied_at=resp
        )
        
    async def GetCurrentState(self, request, context):
        from switcher.backend import is_service_active
        import psutil
        
        active_svcs = {}
        profile_name = self.controller.reconciler.active_profile_name or ""
        if profile_name in self.controller.config.profiles:
            prof = self.controller.config.profiles[profile_name]
            for svc in prof.services:
                active_svcs[svc] = await asyncio.to_thread(is_service_active, svc)
                
        return citadel_pb2.SystemState(
            active_profile=profile_name,
            active_services=active_svcs,
            uptime_seconds=float(time.time() - psutil.boot_time())
        )

    async def StreamTelemetry(self, request, context):
        """Pulse streaming logic — high performance generator."""
        import psutil
        from switcher.backend import get_gpu_vitals
        last_net = psutil.net_io_counters(pernic=True)
        last_time = time.time()
        
        while True:
            vitals = await asyncio.to_thread(get_system_vitals_snapshot)
            gpu = await asyncio.to_thread(get_gpu_vitals)
            
            ts = timestamp_pb2.Timestamp()
            curr_time = time.time()
            ts.FromSeconds(int(curr_time))
            
            cpu_heatmap = citadel_pb2.CPUHeatmap(core_usage=vitals.get("cores", []))
            
            gpu_vitals = citadel_pb2.GPUVitals(
                temperature=float(gpu.get("temp", 0)),
                power_draw_watts=float(gpu.get("power", 0)),
                vram_used_bytes=int(gpu.get("vram_used", 0) * 1024 * 1024),
                vram_total_bytes=int(gpu.get("vram_total", 0) * 1024 * 1024),
                utilization_percent=float(gpu.get("load", 0)),
                fan_speed_percent=float(gpu.get("fan", 0))
            )
            
            ram = psutil.virtual_memory()
            ram_vitals = citadel_pb2.RAMVitals(
                used_bytes=ram.used,
                total_bytes=ram.total
            )
            
            curr_net = psutil.net_io_counters(pernic=True)
            dt = curr_time - last_time
            if dt <= 0: dt = 1.0
            
            bytes_diff = 0
            for iface, counters in curr_net.items():
                if iface == 'lo' or iface.startswith('docker') or iface.startswith('br-'):
                    continue
                last_counters = last_net.get(iface)
                if last_counters:
                    bytes_diff += (counters.bytes_sent - last_counters.bytes_sent) + (counters.bytes_recv - last_counters.bytes_recv)
            
            net_speed_bytes = bytes_diff / dt
            last_net = curr_net
            last_time = curr_time
            
            pulse = citadel_pb2.TelemetryPulse(
                timestamp=ts,
                cpu=cpu_heatmap,
                gpu=gpu_vitals,
                ram=ram_vitals,
                disk_pressure=float(vitals.get("disk_pressure", 0.0)),
                net_speed_bytes_sec=float(net_speed_bytes),
                top_process=vitals.get("top_process", "")
            )
            yield pulse
            
            # Use requested interval or default 1s
            interval = request.interval_ms / 1000.0 if request.interval_ms > 0 else 1.0
            await asyncio.sleep(interval)

async def serve():
    """Bootstrap the Google-grade Control Plane."""
    server = grpc.aio.server()
    controller = CitadelController()
    
    citadel_pb2_grpc.add_CitadelServiceServicer_to_server(CitadelHubService(controller), server)
    server.add_insecure_port('[::]:50051')
    
    recon_task = asyncio.create_task(controller.reconciler.start())
    
    print("[CITADEL_HUB] APEX_CONTROL_PLANE listening on port 50051")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
