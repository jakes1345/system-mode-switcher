"""Backend operations — service management, system tweaks, GPU control.

No GTK imports. All functions are safe to call from any thread.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


import time
import types
import psutil

from switcher.plugins.phase1_bootloader import Phase1Bootloader
from switcher.plugins.phase2_kernel_silicon import Phase2KernelSilicon
from switcher.plugins.phase3_storage_zfs import Phase3StorageZfs
from switcher.plugins.phase4_wayland_graphics import Phase4WaylandGraphics
from switcher.plugins.phase5_redteam_network import Phase5RedteamNetwork
from switcher.plugins.phase6_hyper_orchestration import Phase6HyperOrchestration
from switcher.plugins.phase7_ui_telemetry import Phase7UiTelemetry
from switcher.plugins.phase8_package_manager import Phase8PackageManager
from switcher.plugins.phase9_autonomous_ai import Phase9AutonomousAi
from switcher.plugins.phase10_edge_cases import Phase10EdgeCases

# ── GPU Detection ─────────────────────────────────────────────────────────

def detect_gpu_vendor() -> str:
    """Return 'nvidia', 'amd', 'intel' or 'unknown'."""
    try:
        if shutil.which("nvidia-smi"): return "nvidia"
        if Path("/sys/class/drm/card0/device/vendor").exists():
            vendor = Path("/sys/class/drm/card0/device/vendor").read_text().strip()
            if "0x1002" in vendor: return "amd"
            if "0x8086" in vendor: return "intel"
    except OSError:
        pass
    if shutil.which("lact"): return "amd"
    return "unknown"

def get_primary_interface() -> str:
    """Detect the most likely active physical interface."""
    for root, dirs, _ in os.walk("/sys/class/net"):
        for d in dirs:
            if d.startswith(("wl", "en", "eth", "wlan")):
                # Filter out virtual/loopback
                if Path(f"/sys/class/net/{d}/device").exists():
                    return d
    return "wlan0"

GPU_VENDOR = detect_gpu_vendor()

# ── Citadel Telemetry Engine — High-Performance (0-Blocking) ──────────────

def get_system_vitals_snapshot() -> dict:
    """Take a single, unified snapshot of system telemetry."""
    vitals = {
        "cpu_total": 0,
        "cores": [],
        "disk_pressure": 0.0,
        "top_process": ""
    }
    try:
        # psutil maintains independent timers for percpu=True/False and times
        percents = psutil.cpu_percent(interval=None, percpu=True)
        if percents:
            vitals["cores"] = [int(p) for p in percents]
            vitals["cpu_total"] = int(sum(percents) / len(percents))
            
        times = psutil.cpu_times_percent(interval=None)
        vitals["disk_pressure"] = round(float(times.iowait if hasattr(times, "iowait") else 0), 2)
        
        # Heavy Hitter Process
        r = subprocess.run(["ps", "-eo", "pcpu,comm", "--sort=-pcpu", "--no-headers"], capture_output=True, text=True, timeout=1)
        if r.returncode == 0 and r.stdout:
            parts = r.stdout.strip().splitlines()[0].split(maxsplit=1)
            if len(parts) == 2:
                vitals["top_process"] = f"{parts[1]} ({parts[0]}%)"
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError, IndexError):
        pass
    return vitals

_NVIDIA_CACHE: dict = {"data": {}, "last_run": 0}

def get_gpu_vitals() -> dict:
    """Hardened GPU telemetry with /sys/ fallbacks and NVIDIA caching."""
    global _NVIDIA_CACHE
    vitals = {"temp": 0, "power": 0, "vram_used": 0, "vram_total": 0, "load": 0}
    
    if GPU_VENDOR == "nvidia":
        now = time.time()
        if now - _NVIDIA_CACHE["last_run"] < 0.5:
            return _NVIDIA_CACHE["data"]
            
        try:
            cmd = ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,memory.used,memory.total,utilization.gpu,fan.speed", "--format=csv,noheader,nounits"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
            if r.returncode == 0:
                parts = [p.strip() for p in r.stdout.split(",")]
                if len(parts) >= 6:
                    # Sometimes fan speed can be "[Not Supported]", handle gracefully
                    try:
                        fan = int(parts[5])
                    except ValueError:
                        fan = 0
                    res = {
                        "temp": int(parts[0]), "power": float(parts[1]),
                        "vram_used": int(parts[2]), "vram_total": int(parts[3]),
                        "load": int(parts[4]), "fan": fan
                    }
                    _NVIDIA_CACHE = {"data": res, "last_run": now}
                    return res
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
    
    elif GPU_VENDOR == "amd":
        try:
            # Find the correct AMD card
            target_card = None
            for card in Path("/sys/class/drm").glob("card[0-9]*"):
                vendor_file = card / "device" / "vendor"
                if vendor_file.exists() and "0x1002" in vendor_file.read_text():
                    target_card = card
                    break
            
            if target_card:
                hwmon_dirs = list((target_card / "device" / "hwmon").glob("hwmon*"))
                if hwmon_dirs:
                    hwmon = hwmon_dirs[0]
                    temp_file = hwmon / "temp1_input"
                    if temp_file.exists():
                        vitals["temp"] = int(temp_file.read_text()) // 1000
                    power_file = hwmon / "power1_average"
                    if power_file.exists():
                        vitals["power"] = int(power_file.read_text()) / 1000000
                
                busy_file = target_card / "device" / "gpu_busy_percent"
                if busy_file.exists():
                    vitals["load"] = int(busy_file.read_text())
        except (OSError, IndexError, AttributeError, ValueError):
            pass

    elif GPU_VENDOR == "intel":
        try:
            freq_file = Path("/sys/class/drm/card0/gt_cur_freq_mhz")
            max_freq_file = Path("/sys/class/drm/card0/gt_max_freq_mhz")
            if freq_file.exists() and max_freq_file.exists():
                cur = int(freq_file.read_text().strip())
                mx = int(max_freq_file.read_text().strip())
                vitals["load"] = int((cur / mx) * 100) if mx > 0 else 0
            
            # Temp probing
            for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
                name_file = hwmon / "name"
                if name_file.exists() and ("coretemp" in name_file.read_text() or "intel" in name_file.read_text()):
                    t_file = hwmon / "temp1_input"
                    if t_file.exists():
                        vitals["temp"] = int(t_file.read_text()) // 1000
                        break
        except (OSError, ValueError):
            pass

    return vitals



# ── Service Management ────────────────────────────────────────────────────


def is_service_active(name: str) -> bool:
    """Check if a systemd service is active (and NOT frozen)."""
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5,
        )
        if r.stdout.strip() != "active":
            return False
        # Ensure it's not frozen
        r2 = subprocess.run(["systemctl", "show", "-p", "FreezerState", name], capture_output=True, text=True)
        if "FreezerState=frozen" in r2.stdout:
            return False
        return True
    except (subprocess.TimeoutExpired, OSError):
        return False

def is_service_frozen(name: str) -> bool:
    """Check if a systemd service is currently frozen via Cgroups v2."""
    try:
        r = subprocess.run(["systemctl", "show", "-p", "FreezerState", name], capture_output=True, text=True, timeout=5)
        return "FreezerState=frozen" in r.stdout
    except (subprocess.TimeoutExpired, OSError):
        return False

def is_process_running(grep_pattern: str) -> bool:
    """Check if a process matching the grep pattern is running."""
    try:
        r = subprocess.run(
            ["pgrep", "-f", grep_pattern],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False

def is_process_frozen(proc_id: str) -> bool:
    """Check if a raw process is frozen in its custom Citadel Cryo cgroup."""
    try:
        events = Path(f"/sys/fs/cgroup/citadel_cryo_{proc_id}/cgroup.events")
        if events.exists():
            return "frozen 1" in events.read_text()
    except OSError:
        pass
    return False


# ── System Tweaks ─────────────────────────────────────────────────────────


def get_swappiness() -> int:
    """Read current vm.swappiness."""
    try:
        return int(Path("/proc/sys/vm/swappiness").read_text().strip())
    except (OSError, ValueError):
        return 30


def get_compositor_unredirect() -> bool:
    """Check Cinnamon/Muffin unredirect-fullscreen-windows setting."""
    try:
        r = subprocess.run(
            ["gsettings", "get", "org.cinnamon.muffin", "unredirect-fullscreen-windows"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() == "true"
    except (subprocess.TimeoutExpired, OSError):
        return False


def get_gpu_performance_mode() -> bool | None:
    """Check GPU performance mode. Returns None if unsupported."""
    if GPU_VENDOR == "nvidia":
        try:
            r = subprocess.run(
                ["nvidia-settings", "-t", "-q", "[gpu:0]/GpuPowerMizerMode"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                return int(r.stdout.strip()) == 1
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        return None
    elif GPU_VENDOR == "amd":
        try:
            r = subprocess.run(
                ["lact", "info"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                return "performance" in r.stdout.lower()
        except (subprocess.TimeoutExpired, OSError):
            pass
        return None
    return None


# ── System Info ───────────────────────────────────────────────────────────


def get_ram_info() -> tuple[float, float]:
    """Return (used_gb, total_gb) from /proc/meminfo."""
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                info[parts[0].rstrip(":")] = int(parts[1])
        total_kb = info.get("MemTotal", 0)
        available_kb = info.get("MemAvailable", total_kb)
        total_gb = total_kb / 1048576
        used_gb = (total_kb - available_kb) / 1048576
        return round(used_gb, 1), round(total_gb, 1)
    except (OSError, ValueError):
        return 0.0, 0.0




# ── Hardware Tunnels (Kernel-Side) ────────────────────────────────────────

def set_cpu_governor(governor: str) -> str:
    """Force CPU governor across all cores via sysfs."""
    try:
        path = "/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
        cmd = f"for f in {path}; do echo {governor} > $f; done"
        return cmd
    except (OSError, ValueError):
        return ""

def set_gpu_power_limit(watts: int) -> str:
    """Set NVIDIA power limit in Watts."""
    if GPU_VENDOR != "nvidia": return ""
    return f"nvidia-smi -pl {watts}"

def set_kernel_thp(mode: str) -> str:
    """Tune Transparent Hugepages (always | madvise | never)."""
    return f"echo {mode} > /sys/kernel/mm/transparent_hugepage/enabled"

# ── Enhanced Apply Logic ──────────────────────────────────────────────────

def get_hardware_report() -> str:
    """Read actual kernel/hardware state to verify changes."""
    report = []
    try:
        # 1. CPU
        gov_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
        if gov_path.exists():
            report.append(f"[CONFIRM] CPU_GOVERNOR: {gov_path.read_text().strip().upper()}")
        
        # 2. THP
        thp_path = Path("/sys/kernel/mm/transparent_hugepage/enabled")
        if thp_path.exists():
            thp = thp_path.read_text()
            matches = [m.strip("[]") for m in thp.split() if "[" in m]
            if matches:
                report.append(f"[CONFIRM] KERNEL_THP: {matches[0].upper()}")

        # 3. GPU
        if GPU_VENDOR == "nvidia":
            r = subprocess.run(["nvidia-smi", "--query-gpu=power.limit", "--format=csv,noheader"], capture_output=True, text=True)
            if r.returncode == 0:
                report.append(f"[CONFIRM] GPU_POWER_LIMIT: {r.stdout.strip()}")
                
    except (OSError, subprocess.SubprocessError, IndexError, ValueError) as e:
        report.append(f"[AUDIT_ERROR] {e}")
    
    return "\n".join(report)

# ── Enhanced Apply Logic ──────────────────────────────────────────────────

def build_apply_script(
    services_to_start: list[str],
    services_to_stop: list[str],
    services_to_freeze: list[str],
    processes_to_start: list[tuple[str, str]],
    processes_to_kill: list[tuple[str, str]],
    processes_to_freeze: list[tuple[str, str]],
    swappiness: int | None,
    compositor_unredirect: bool | None,
    gpu_performance: bool | None,
    cpu_governor: str | None = "performance",
    gpu_power_limit: int | None = None,
    thp_mode: str | None = "madvise",
    stealth_mode: bool = False,
    gaming_audio: bool = False,
    cpu_shielding: bool = False,
    wipe_ram: bool = False,
    dirty_ratio: int = 20,
    dirty_background_ratio: int = 10,
) -> str:
    """Build a hardened bash script for hardware-level orchestration using the Plugin Engine."""
    lines = ["#!/bin/bash", "set -e", ""]
    
    # ── Environment Ingress ──
    shadow_root = os.environ.get("SHADOW_ROOT", os.path.expanduser("~/ShadowCypher"))
    if os.path.isdir(shadow_root):
        lines.append(f"export PYTHONPATH=$PYTHONPATH:{shadow_root}")
        lines.append(f"export SHADOW_ROOT={shadow_root}")
        lines.append("")

    # Wrap arguments into a config object for the plugins
    config = types.SimpleNamespace(
        services_to_start=services_to_start,
        services_to_stop=services_to_stop,
        services_to_freeze=services_to_freeze,
        processes_to_start=processes_to_start,
        processes_to_kill=processes_to_kill,
        processes_to_freeze=processes_to_freeze,
        swappiness=swappiness,
        compositor_unredirect=compositor_unredirect,
        gpu_performance=gpu_performance,
        cpu_governor=cpu_governor,
        gpu_power_limit=gpu_power_limit,
        thp_mode=thp_mode,
        stealth_mode=stealth_mode,
        gaming_audio=gaming_audio,
        cpu_shielding=cpu_shielding,
        wipe_ram=wipe_ram,
        dirty_ratio=dirty_ratio,
        dirty_background_ratio=dirty_background_ratio
    )

    # Instantiate all 10 phases
    phases = [
        Phase1Bootloader(config),
        Phase2KernelSilicon(config),
        Phase3StorageZfs(config),
        Phase4WaylandGraphics(config),
        Phase5RedteamNetwork(config),
        Phase6HyperOrchestration(config),
        Phase7UiTelemetry(config),
        Phase8PackageManager(config),
        Phase9AutonomousAi(config),
        Phase10EdgeCases(config)
    ]

    # Run the Plugin Engine
    lines.append("echo 'CITADEL ORCHESTRATION STARTING...'")
    for phase in phases:
        phase.apply(lines)
        
    # ── Legacy Process/Service Orchestration (Phase 6 overflow) ───────
    
    for svc in services_to_stop:
        lines.append(f"systemctl stop {svc} 2>/dev/null || true")
    for svc in services_to_freeze:
        lines.append(f"systemctl freeze {svc} 2>/dev/null || true")
    for svc in services_to_start:
        lines.append(f"systemctl thaw {svc} 2>/dev/null || true")
        lines.append(f"systemctl start {svc} 2>/dev/null || true")
        
    for proc_id, grep_pattern in processes_to_kill:
        lines.append(f"pkill -f '{grep_pattern}' 2>/dev/null || true")
        lines.append(f"rmdir /sys/fs/cgroup/citadel_cryo_{proc_id} 2>/dev/null || true")
        
    for proc_id, grep_pattern in processes_to_freeze:
        lines.append(f"mkdir -p /sys/fs/cgroup/citadel_cryo_{proc_id}")
        lines.append(f"for pid in $(pgrep -f '{grep_pattern}' 2>/dev/null); do")
        lines.append(f"    echo $pid > /sys/fs/cgroup/citadel_cryo_{proc_id}/cgroup.procs 2>/dev/null || true")
        lines.append("done")
        lines.append(f"echo 1 > /sys/fs/cgroup/citadel_cryo_{proc_id}/cgroup.freeze 2>/dev/null || true")
        
    for proc_id, start_cmd in processes_to_start:
        lines.append(f"echo 0 > /sys/fs/cgroup/citadel_cryo_{proc_id}/cgroup.freeze 2>/dev/null || true")
        if start_cmd:
            lines.append(f"if ! pgrep -f '{proc_id}' >/dev/null 2>&1; then")
            lines.append(f"    nohup {start_cmd} >/dev/null 2>&1 &")
            lines.append(f"fi")

    lines.append('echo "RECONCILE_SUCCESS"')
    return "\n".join(lines)


def run_apply_script(script_content: str, sudo_password: str | None = None) -> tuple[bool, str]:
    """Write script to temp file, run via bash (if root) or pkexec, return (success, output)."""
    fd, path = tempfile.mkstemp(prefix="switcher-apply-", suffix=".sh")
    try:
        os.write(fd, script_content.encode())
        os.close(fd)
        os.chmod(path, 0o755)

        if os.geteuid() == 0:
            # We are root (running as systemd OS daemon)
            r = subprocess.run(
                ["bash", path],
                capture_output=True, text=True, timeout=120,
            )
            output = r.stdout.strip()
            if r.returncode != 0:
                output += "\n" + r.stderr.strip()
            return r.returncode == 0, output

        # Try pkexec first with the trusted policy wrapper
        try:
            r = subprocess.run(
                ["pkexec", "/usr/local/bin/citadel-apply", path],
                capture_output=True, text=True, timeout=120,
            )
            output = r.stdout.strip()
            if r.returncode != 0:
                output += "\n" + r.stderr.strip()
            # If pkexec succeeded or user cancelled (126), return
            if r.returncode == 0 or r.returncode == 126:
                return r.returncode == 0, output
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Fallback to sudo -S if pkexec failed and we have a password
        if sudo_password:
            r = subprocess.run(
                ["sudo", "-S", "bash", path],
                input=sudo_password + "\n",
                capture_output=True, text=True, timeout=120,
            )
            output = r.stdout.strip()
            if r.returncode != 0:
                # Filter out the password prompt from stderr
                stderr_lines = [
                    l for l in r.stderr.strip().splitlines()
                    if not l.startswith("[sudo]")
                ]
                if stderr_lines:
                    output += "\n" + "\n".join(stderr_lines)
            return r.returncode == 0, output

        return False, "pkexec failed and no sudo password available"
    except subprocess.TimeoutExpired:
        return False, "Apply timed out after 120s"
    except OSError as e:
        return False, str(e)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def set_compositor_unredirect(value: bool) -> tuple[bool, str]:
    """Set Cinnamon compositor unredirect (runs as current user, no pkexec)."""
    val = "true" if value else "false"
    try:
        r = subprocess.run(
            ["gsettings", "set", "org.cinnamon.muffin",
             "unredirect-fullscreen-windows", val],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0, r.stderr.strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)


def set_nvidia_gpu_mode(performance: bool) -> tuple[bool, str]:
    """Set NVIDIA GPU power mode (runs as current user, no pkexec)."""
    mode = "1" if performance else "0"
    try:
        r = subprocess.run(
            ["nvidia-settings", "-a", f"[gpu:0]/GpuPowerMizerMode={mode}"],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0, r.stderr.strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)


# ── Stealth & Audio Tweaks ──────────────────────────────────────────────


def randomize_mac(interface: str = "wlan0") -> str:
    """Build bash to randomize MAC and return it. Only builds, doesn't execute."""
    return f"ip link set {interface} down && ip link set {interface} address $(printf '00:60:2f:%02x:%02x:%02x' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256))) && ip link set {interface} up"


def restore_mac(interface: str, original_mac: str) -> str:
    """Build bash to restore MAC."""
    return f"ip link set {interface} down && ip link set {interface} address {original_mac} && ip link set {interface} up"


def set_audio_latency(gaming: bool) -> str:
    """Build bash for Pipewire/Pulse low latency tweaks."""
    val = -19 if gaming else 0
    return f"pid=$(pgrep pipewire | head -n 1 2>/dev/null); [ -n \"$pid\" ] && echo {val} > /proc/$pid/nice 2>/dev/null || true"

