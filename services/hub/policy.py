"""
Hub trust policy — what the root daemon accepts from where.

Anything that becomes a shell command (process start/stop/grep, the set of
manageable services) comes only from a root-owned system config or the built-in
defaults. The desktop user's file and dashboard requests contribute data only:
booleans for known services/processes and validated tweak values.
"""

from __future__ import annotations

import copy
import os
import stat
from pathlib import Path

from switcher.config import Config, ProfileConfig, TweakConfig, load_config

SYSTEM_CONFIG_PATH = Path(os.environ.get("CITADEL_SYSTEM_CONFIG", "/etc/obsidian-citadel/citadel.toml"))

VALID_GOVERNORS = {"performance", "powersave", "schedutil", "ondemand", "conservative"}
VALID_THP = {"always", "madvise", "never"}


def untrusted_reason(path: Path, trusted_uids: tuple[int, ...] = (0,)) -> str | None:
    """Why `path` can't be trusted to hold root commands, or None if it can.

    The file and every parent directory must be owned by a trusted uid (root) and
    not group/world-writable, otherwise someone else could swap its contents.
    """
    try:
        path = path.resolve(strict=True)
    except OSError as e:
        return f"cannot resolve {path}: {e}"
    for p in [path, *path.parents]:
        try:
            st = p.stat()
        except OSError as e:
            return f"cannot stat {p}: {e}"
        if st.st_uid not in trusted_uids:
            return f"{p} is not owned by root"
        # A root-owned sticky dir (/tmp) is fine: others can't rename or replace entries in it
        sticky_root_dir = p != path and st.st_uid == 0 and st.st_mode & stat.S_ISVTX
        if st.st_mode & 0o022 and not sticky_root_dir:
            return f"{p} is group/world-writable"
    return None


def _int_in(value, low: int, high: int, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if low <= value <= high else default


def sanitize_tweaks(t: TweakConfig) -> TweakConfig:
    """Clamp tweak values to known-safe ones; they are interpolated into a root script."""
    d = TweakConfig()
    return TweakConfig(
        swappiness=_int_in(t.swappiness, 0, 200, d.swappiness),
        compositor_unredirect=bool(t.compositor_unredirect),
        gpu_performance=bool(t.gpu_performance),
        cpu_governor=t.cpu_governor if t.cpu_governor in VALID_GOVERNORS else d.cpu_governor,
        gpu_power_limit=(_int_in(t.gpu_power_limit, 1, 1000, 0) or None) if t.gpu_power_limit is not None else None,
        thp_mode=t.thp_mode if t.thp_mode in VALID_THP else d.thp_mode,
        stealth_mode=bool(t.stealth_mode),
        gaming_audio=bool(t.gaming_audio),
        cpu_shielding=bool(t.cpu_shielding),
        clear_ram_on_exit=bool(t.clear_ram_on_exit),
        dirty_ratio=_int_in(t.dirty_ratio, 0, 100, d.dirty_ratio),
        dirty_background_ratio=_int_in(t.dirty_background_ratio, 0, 100, d.dirty_background_ratio),
    )


def sanitize_profile(profile: ProfileConfig, config: Config) -> tuple[ProfileConfig, list[str]]:
    """Keep only known services/processes and safe tweak values."""
    notes: list[str] = []
    known_services = {s.name for s in config.services}
    known_procs = {p.id for p in config.processes}
    clean = copy.deepcopy(profile)
    clean.services = {}
    for svc, on in profile.services.items():
        if svc in known_services:
            clean.services[svc] = bool(on)
        else:
            notes.append(f"ignored unknown service '{svc}'")
    clean.processes = {}
    for proc, on in profile.processes.items():
        if proc in known_procs:
            clean.processes[proc] = bool(on)
        else:
            notes.append(f"ignored unknown process '{proc}'")
    clean.tweaks = sanitize_tweaks(profile.tweaks)
    for field in ("cpu_governor", "thp_mode"):
        if getattr(profile.tweaks, field) != getattr(clean.tweaks, field):
            notes.append(f"ignored invalid {field} '{getattr(profile.tweaks, field)}'")
    return clean, notes


def load_hub_config(user_path: Path, system_path: Path = SYSTEM_CONFIG_PATH,
                    trusted_uids: tuple[int, ...] = (0,)) -> tuple[Config, list[str]]:
    """Services/processes from the root-owned system config (or defaults);
    profiles from the user's file, sanitized."""
    notes: list[str] = []
    defaults = Path("/nonexistent/obsidian-citadel.toml")
    system_src = defaults
    if system_path.exists():
        reason = untrusted_reason(system_path, trusted_uids)
        if reason:
            notes.append(f"refusing system config {system_path}: {reason}; using built-in services/processes")
        else:
            system_src = system_path
    system = load_config(system_src)
    if system.load_error:
        notes.append(system.load_error)

    user = load_config(user_path)
    config = Config(
        services=system.services,
        processes=system.processes,
        profiles={},
        config_path=user_path,
        load_error=user.load_error,
    )
    for name, prof in user.profiles.items():
        clean, prof_notes = sanitize_profile(prof, config)
        config.profiles[name] = clean
        notes.extend(f"profile '{name}': {n}" for n in prof_notes)
    return config, notes
