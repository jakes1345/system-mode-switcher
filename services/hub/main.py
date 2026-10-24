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
import pwd
from google.protobuf import timestamp_pb2
from switcher.backend import get_system_vitals_snapshot
from services.hub.policy import VALID_GOVERNORS, VALID_THP, load_hub_config, sanitize_profile
from services.hub.reconciler import CitadelReconciler
from switcher.config import ProfileConfig, default_config_path, hub_socket_path
from switcher.core.logger import logger


class CitadelController:
    """The 'Brain' — Reconciles Desired State vs Actual State."""
    def __init__(self):
        # Profiles come from the desktop user's file (CITADEL_CONFIG); anything that
        # becomes a root command comes from the root-owned system config — see policy.py
        self.config_path = default_config_path()
        self._config_mtime = None
        self.config, notes = load_hub_config(self.config_path)
        self._config_mtime = self._mtime()
        self._log_notes(notes)
        logger.info("Hub", f"Loaded profiles from {self.config_path}")
        self.reconciler = CitadelReconciler(self.config)

    @staticmethod
    def _log_notes(notes: list[str]) -> None:
        for note in notes:
            logger.warn("Hub", note)

    def _mtime(self):
        try:
            return self.config_path.stat().st_mtime
        except OSError:
            return None

    def reload_config_if_changed(self) -> None:
        """Pick up profiles the dashboard saved since the last load."""
        mtime = self._mtime()
        if mtime == self._config_mtime:
            return
        fresh, notes = load_hub_config(self.config_path)
        if fresh.load_error:
            logger.error("Hub", f"Keeping previous config: {fresh.load_error}")
            return
        self._log_notes(notes)
        self.config = fresh
        self._config_mtime = mtime
        self.reconciler.config = fresh
        logger.info("Hub", f"Reloaded profiles from {self.config_path}")

    def resolve_profile(self, name: str, overrides) -> tuple[ProfileConfig | None, list[str]]:
        """Named profile with the dashboard's switch state layered on top.

        The result goes through the same sanitizer as file profiles: only known
        services/processes and safe tweak values reach the root script.
        """
        base = self.config.profiles.get(name)
        if base is None and overrides is None:
            return None, [f"Unknown profile '{name}' (config: {self.config_path})"]
        profile = copy.deepcopy(base) if base else ProfileConfig(name=name or "Custom")
        notes: list[str] = []
        if overrides is not None:
            profile.services.update(overrides.services)
            profile.processes.update(overrides.processes)
            t = profile.tweaks
            for field in ("swappiness", "compositor_unredirect", "gpu_performance", "gpu_power_limit"):
                if overrides.HasField(field):
                    setattr(t, field, getattr(overrides, field))
            # An invalid choice keeps the profile's own value rather than the default
            for field, valid in (("cpu_governor", VALID_GOVERNORS), ("thp_mode", VALID_THP)):
                if overrides.HasField(field):
                    value = getattr(overrides, field)
                    if value in valid:
                        setattr(t, field, value)
                    else:
                        notes.append(f"ignored invalid {field} '{value}'")
        profile, sanitize_notes = sanitize_profile(profile, self.config)
        return profile, notes + sanitize_notes


def socket_owner_uid() -> int | None:
    """The desktop user allowed to talk to the hub (CITADEL_USER), else the owner
    of the directory holding their config. None = root only."""
    user = os.environ.get("CITADEL_USER")
    if user:
        try:
            return pwd.getpwnam(user).pw_uid
        except KeyError:
            logger.error("Hub", f"CITADEL_USER '{user}' does not exist; hub socket is root-only")
            return None
    try:
        uid = default_config_path().parent.stat().st_uid
    except OSError:
        return None
    return uid or None


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

def bind_hub_socket(server, path: Path, owner_uid: int | None) -> None:
    """Listen on a unix socket only `owner_uid` (and root) can connect to.

    Filesystem permissions are the authentication: no TCP port, nothing on the network.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_socket():
        path.unlink()  # stale socket from a previous run
    old_umask = os.umask(0o177)  # socket is born 0600, no window where others can connect
    try:
        server.add_insecure_port(f"unix://{path}")
    finally:
        os.umask(old_umask)
    if owner_uid is not None and os.geteuid() == 0:
        os.chown(path, owner_uid, -1)
    os.chmod(path, 0o600)


async def serve():
    """Bootstrap the Google-grade Control Plane."""
    server = grpc.aio.server()
    controller = CitadelController()

    citadel_pb2_grpc.add_CitadelServiceServicer_to_server(CitadelHubService(controller), server)
    sock = hub_socket_path()
    bind_hub_socket(server, sock, socket_owner_uid())

    recon_task = asyncio.create_task(controller.reconciler.start())

    print(f"[CITADEL_HUB] APEX_CONTROL_PLANE listening on unix://{sock}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
