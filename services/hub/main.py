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

import copy
from google.protobuf import timestamp_pb2
from switcher.backend import get_system_vitals_snapshot
from services.hub.reconciler import CitadelReconciler
from switcher.config import ProfileConfig, default_config_path, load_config
from switcher.core.logger import logger

VALID_GOVERNORS = {"performance", "powersave", "schedutil", "ondemand", "conservative"}
VALID_THP = {"always", "madvise", "never"}


class CitadelController:
    """The 'Brain' — Reconciles Desired State vs Actual State."""
    def __init__(self):
        # The hub runs as root; CITADEL_CONFIG points it at the desktop user's file
        self.config_path = default_config_path()
        self._config_mtime = None
        self.config = load_config(self.config_path)
        self._config_mtime = self._mtime()
        logger.info("Hub", f"Loaded config from {self.config_path}")
        self.reconciler = CitadelReconciler(self.config)

    def _mtime(self):
        try:
            return self.config_path.stat().st_mtime
        except OSError:
            return None

    def reload_config_if_changed(self) -> None:
        """Pick up profiles/processes the dashboard saved since the last load."""
        mtime = self._mtime()
        if mtime == self._config_mtime:
            return
        fresh = load_config(self.config_path)
        if fresh.load_error:
            logger.error("Hub", f"Keeping previous config: {fresh.load_error}")
            return
        self.config = fresh
        self._config_mtime = mtime
        self.reconciler.config = fresh
        logger.info("Hub", f"Reloaded config from {self.config_path}")

    def resolve_profile(self, name: str, overrides) -> tuple[ProfileConfig | None, list[str]]:
        """Named profile from config with the dashboard's switch state layered on top.

        Overrides are validated: only known services/processes and sane tweak
        values get through, since they end up in a root shell script.
        """
        notes: list[str] = []
        base = self.config.profiles.get(name)
        if base is None and overrides is None:
            return None, [f"Unknown profile '{name}' (config: {self.config_path})"]
        profile = copy.deepcopy(base) if base else ProfileConfig(name=name or "Custom")
        if overrides is None:
            return profile, notes

        known_services = {s.name for s in self.config.services}
        for svc, on in overrides.services.items():
            if svc in known_services:
                profile.services[svc] = on
            else:
                notes.append(f"ignored unknown service '{svc}'")
        known_procs = {p.id for p in self.config.processes}
        for proc, on in overrides.processes.items():
            if proc in known_procs:
                profile.processes[proc] = on
            else:
                notes.append(f"ignored unknown process '{proc}'")

        t = profile.tweaks
        if overrides.HasField("swappiness") and 0 <= overrides.swappiness <= 200:
            t.swappiness = overrides.swappiness
        if overrides.HasField("compositor_unredirect"):
            t.compositor_unredirect = overrides.compositor_unredirect
        if overrides.HasField("gpu_performance"):
            t.gpu_performance = overrides.gpu_performance
        if overrides.HasField("cpu_governor"):
            if overrides.cpu_governor in VALID_GOVERNORS:
                t.cpu_governor = overrides.cpu_governor
            else:
                notes.append(f"ignored invalid governor '{overrides.cpu_governor}'")
        if overrides.HasField("gpu_power_limit") and 0 < overrides.gpu_power_limit <= 1000:
            t.gpu_power_limit = overrides.gpu_power_limit
        if overrides.HasField("thp_mode"):
            if overrides.thp_mode in VALID_THP:
                t.thp_mode = overrides.thp_mode
            else:
                notes.append(f"ignored invalid THP mode '{overrides.thp_mode}'")
        return profile, notes

class CitadelHubService(citadel_pb2_grpc.CitadelServiceServicer):
    """The gRPC Service implementation."""
    def __init__(self, controller: CitadelController):
        self.controller = controller

    async def SetProfile(self, request, context):
        controller = self.controller
        controller.reload_config_if_changed()
        overrides = request.overrides if request.HasField("overrides") else None
        profile, notes = controller.resolve_profile(request.profile_name, overrides)

        resp = timestamp_pb2.Timestamp()
        resp.FromSeconds(int(time.time()))
        if profile is None:
            return citadel_pb2.ProfileResponse(success=False, message="; ".join(notes), applied_at=resp)

        # Runs the apply to completion so the dashboard gets the real result
        ok, output = await controller.reconciler.set_profile(profile)
        status = "applied — reconciler enforcing state" if ok else "FAILED to apply"
        message = f"Profile '{profile.name}' {status}."
        if notes:
            message += " (" + "; ".join(notes) + ")"
        return citadel_pb2.ProfileResponse(
            success=ok,
            message=message,
            applied_at=resp,
            output=output[-4000:],
        )

    async def GetCurrentState(self, request, context):
        from switcher.backend import is_service_active
        import psutil
        
        active_svcs = {}
        prof = self.controller.reconciler.desired
        profile_name = prof.name if prof else ""
        if prof:
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
