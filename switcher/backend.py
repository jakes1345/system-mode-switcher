"""Backend operations — service management, system tweaks, GPU control.

No GTK imports. All functions are safe to call from any thread.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


# ── GPU Detection ─────────────────────────────────────────────────────────


def detect_gpu_vendor() -> str:
    """Return 'nvidia', 'amd', or 'unknown'."""
    if shutil.which("nvidia-settings"):
        return "nvidia"
    if shutil.which("lact"):
        return "amd"
    return "unknown"


GPU_VENDOR = detect_gpu_vendor()


# ── Service Management ────────────────────────────────────────────────────


def is_service_active(name: str) -> bool:
    """Check if a systemd service is active."""
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() == "active"
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


def get_cpu_percent() -> int:
    """Quick CPU usage estimate from /proc/stat (two samples, 200ms apart)."""
    import time

    def read_cpu():
        line = Path("/proc/stat").read_text().splitlines()[0]
        vals = list(map(int, line.split()[1:]))
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        total = sum(vals)
        return idle, total

    try:
        idle1, total1 = read_cpu()
        time.sleep(0.2)
        idle2, total2 = read_cpu()
        idle_delta = idle2 - idle1
        total_delta = total2 - total1
        if total_delta == 0:
            return 0
        return round((1 - idle_delta / total_delta) * 100)
    except (OSError, ValueError, IndexError):
        return 0


# ── Apply Changes ─────────────────────────────────────────────────────────


def build_apply_script(
    services_to_start: list[str],
    services_to_stop: list[str],
    processes_to_start: list[tuple[str, str]],  # (id, start_cmd)
    processes_to_kill: list[tuple[str, str]],    # (id, grep_pattern)
    swappiness: int | None,
    compositor_unredirect: bool | None,
    gpu_performance: bool | None,
) -> str:
    """Build a bash script that applies all changes. Returns script content."""
    lines = ["#!/bin/bash", "set -e", ""]

    for svc in services_to_stop:
        lines.append(f'echo "STOP {svc}"')
        lines.append(f"systemctl stop {svc} 2>/dev/null || true")

    for svc in services_to_start:
        lines.append(f'echo "START {svc}"')
        lines.append(f"systemctl start {svc} 2>/dev/null || true")

    for proc_id, grep_pattern in processes_to_kill:
        lines.append(f'echo "KILL {proc_id}"')
        lines.append(f"pkill -f '{grep_pattern}' 2>/dev/null || true")

    for proc_id, start_cmd in processes_to_start:
        lines.append(f'echo "LAUNCH {proc_id}"')
        lines.append(f"nohup {start_cmd} > /dev/null 2>&1 &")

    if swappiness is not None:
        lines.append(f'echo "SWAPPINESS {swappiness}"')
        lines.append(f"sysctl vm.swappiness={swappiness}")

    if gpu_performance is not None and GPU_VENDOR != "unknown":
        if GPU_VENDOR == "amd":
            level = "high" if gpu_performance else "auto"
            lines.append(f'echo "GPU {level}"')
            lines.append(f"lact set-power-profile {level}")

    lines.append('echo "DONE"')
    return "\n".join(lines)


def run_apply_script(script_content: str, sudo_password: str | None = None) -> tuple[bool, str]:
    """Write script to temp file, run via pkexec (or sudo fallback), return (success, output)."""
    fd, path = tempfile.mkstemp(prefix="switcher-apply-", suffix=".sh")
    try:
        os.write(fd, script_content.encode())
        os.close(fd)
        os.chmod(path, 0o755)

        # Try pkexec first
        try:
            r = subprocess.run(
                ["pkexec", "bash", path],
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
