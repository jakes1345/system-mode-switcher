"""TOML configuration loader and saver with validation."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ServiceConfig:
    name: str          # systemd unit name
    display: str       # human-readable label
    description: str   # short description


@dataclass
class ProcessConfig:
    id: str            # unique identifier
    display: str       # human-readable label
    description: str   # short description
    grep: str          # pattern for pgrep -f
    start_cmd: str     # shell command to launch


@dataclass
class TweakConfig:
    swappiness: int = 30
    compositor_unredirect: bool = False
    gpu_performance: bool = False


@dataclass
class ProfileConfig:
    name: str
    description: str = ""
    color: str = "#4fc3f7"
    builtin: bool = False
    services: dict[str, bool] = field(default_factory=dict)
    processes: dict[str, bool] = field(default_factory=dict)
    tweaks: TweakConfig = field(default_factory=TweakConfig)


@dataclass
class Config:
    services: list[ServiceConfig] = field(default_factory=list)
    processes: list[ProcessConfig] = field(default_factory=list)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    config_path: Path = field(default_factory=lambda: Path.home() / "system-mode-switcher.toml")
    load_error: str | None = None


# ── Built-in defaults ────────────────────────────────────────────────────

DEFAULT_SERVICES = [
    ServiceConfig("mysql.service", "MySQL", "Database server"),
    ServiceConfig("postgresql@16-main.service", "PostgreSQL", "Database server"),
    ServiceConfig("docker.service", "Docker", "Container engine"),
    ServiceConfig("containerd.service", "Containerd", "Container runtime"),
    ServiceConfig("godot-server.service", "Godot Server", "Godot headless server"),
    ServiceConfig("php8.3-fpm.service", "PHP-FPM", "PHP process manager"),
    ServiceConfig("postfix@-.service", "Postfix", "Mail server"),
    ServiceConfig("smbd.service", "Samba (SMB)", "File sharing"),
    ServiceConfig("nmbd.service", "Samba (NMB)", "NetBIOS name service"),
    ServiceConfig("tor@default.service", "Tor", "Anonymizing network"),
    ServiceConfig("shadow-cypher.service", "ShadowCypher", "Router admin panel"),
    ServiceConfig("cups.service", "CUPS", "Print service"),
    ServiceConfig("cups-browsed.service", "CUPS Browsed", "Printer discovery"),
    ServiceConfig("tailscaled.service", "Tailscale", "VPN mesh network"),
    ServiceConfig("bluetooth.service", "Bluetooth", "Bluetooth service"),
    ServiceConfig("ModemManager.service", "ModemManager", "Modem manager"),
    ServiceConfig("lactd.service", "LACT", "GPU control daemon"),
    ServiceConfig("ollama.service", "Ollama", "Local LLM runner"),
]

DEFAULT_PROCESSES = [
    ProcessConfig("qdrant", "Qdrant", "Vector database", "qdrant",
                  "qdrant --config-path /etc/qdrant/config.yaml"),
]

_ALL_OFF = {s.name: False for s in DEFAULT_SERVICES}
_KEEP_ON = {"tailscaled.service": True, "bluetooth.service": True, "lactd.service": True}

_SVC_PROGRAMMING = {
    "mysql.service": True, "postgresql@16-main.service": True,
    "docker.service": True, "containerd.service": True,
    "godot-server.service": False, "php8.3-fpm.service": True,
    "postfix@-.service": False, "smbd.service": True, "nmbd.service": True,
    "tor@default.service": False, "shadow-cypher.service": True,
    "cups.service": True, "cups-browsed.service": True,
    "tailscaled.service": True, "bluetooth.service": True,
    "ModemManager.service": False, "lactd.service": True, "ollama.service": False,
}

DEFAULT_PROFILES: dict[str, ProfileConfig] = {
    "Gaming": ProfileConfig(
        name="Gaming",
        description="Maximum FPS. Kills everything non-essential.",
        color="#e74c3c", builtin=True,
        services={**_ALL_OFF, **_KEEP_ON},
        processes={"qdrant": False},
        tweaks=TweakConfig(swappiness=10, compositor_unredirect=True, gpu_performance=True),
    ),
    "Programming": ProfileConfig(
        name="Programming",
        description="Dev tools on, AI services off.",
        color="#2ecc71", builtin=True,
        services=dict(_SVC_PROGRAMMING),
        processes={"qdrant": False},
        tweaks=TweakConfig(swappiness=30),
    ),
    "AI + Dev": ProfileConfig(
        name="AI + Dev",
        description="Everything for AI work + development.",
        color="#9b59b6", builtin=True,
        services={**_SVC_PROGRAMMING, "ollama.service": True},
        processes={"qdrant": True},
        tweaks=TweakConfig(swappiness=30),
    ),
    "Game Dev": ProfileConfig(
        name="Game Dev",
        description="Godot + dev tools, lighter background load.",
        color="#e67e22", builtin=True,
        services={
            "mysql.service": True, "postgresql@16-main.service": False,
            "docker.service": False, "containerd.service": False,
            "godot-server.service": True, "php8.3-fpm.service": False,
            "postfix@-.service": False, "smbd.service": True, "nmbd.service": True,
            "tor@default.service": False, "shadow-cypher.service": False,
            "cups.service": False, "cups-browsed.service": False,
            "tailscaled.service": True, "bluetooth.service": True,
            "ModemManager.service": False, "lactd.service": True, "ollama.service": False,
        },
        processes={"qdrant": False},
        tweaks=TweakConfig(swappiness=30),
    ),
}


def load_config(path: Path | None = None) -> Config:
    """Load config from TOML. Returns defaults on missing/malformed file."""
    config_path = path or Path.home() / "system-mode-switcher.toml"
    config = Config(
        services=list(DEFAULT_SERVICES),
        processes=list(DEFAULT_PROCESSES),
        profiles=dict(DEFAULT_PROFILES),
        config_path=config_path,
    )

    if not config_path.exists():
        return config

    try:
        with open(config_path, "rb") as f:
            raw = tomllib.load(f)
    except Exception:
        return Config(
            services=list(DEFAULT_SERVICES),
            processes=list(DEFAULT_PROCESSES),
            profiles=dict(DEFAULT_PROFILES),
            config_path=config_path,
            load_error=f"Failed to parse {config_path}. Using defaults.",
        )

    # Parse services
    raw_services = raw.get("service", [])
    if raw_services:
        config.services = []
        for s in raw_services:
            config.services.append(ServiceConfig(
                name=s.get("name", "unknown.service"),
                display=s.get("display", s.get("name", "Unknown")),
                description=s.get("description", ""),
            ))

    # Parse processes
    raw_processes = raw.get("process", [])
    if raw_processes:
        config.processes = []
        for p in raw_processes:
            config.processes.append(ProcessConfig(
                id=p.get("id", "unknown"),
                display=p.get("display", p.get("id", "Unknown")),
                description=p.get("description", ""),
                grep=p.get("grep", p.get("id", "")),
                start_cmd=p.get("start_cmd", ""),
            ))

    # Parse profiles
    raw_profiles = raw.get("profile", {})
    if raw_profiles:
        config.profiles = {}
        for name, pdata in raw_profiles.items():
            tweaks_raw = pdata.get("tweaks", {})
            config.profiles[name] = ProfileConfig(
                name=name,
                description=pdata.get("description", ""),
                color=pdata.get("color", "#4fc3f7"),
                builtin=pdata.get("builtin", False),
                services={k: bool(v) for k, v in pdata.get("services", {}).items()},
                processes={k: bool(v) for k, v in pdata.get("processes", {}).items()},
                tweaks=TweakConfig(
                    swappiness=tweaks_raw.get("swappiness", 30),
                    compositor_unredirect=bool(tweaks_raw.get("compositor_unredirect", False)),
                    gpu_performance=bool(tweaks_raw.get("gpu_performance", False)),
                ),
            )

    return config


def save_config(config: Config) -> None:
    """Write current config back to TOML."""
    lines: list[str] = [
        "# System Mode Switcher — Configuration",
        "# Auto-generated. Edit with care.",
        "",
    ]

    for svc in config.services:
        lines.append("[[service]]")
        lines.append(f'name = "{svc.name}"')
        lines.append(f'display = "{svc.display}"')
        lines.append(f'description = "{svc.description}"')
        lines.append("")

    for proc in config.processes:
        lines.append("[[process]]")
        lines.append(f'id = "{proc.id}"')
        lines.append(f'display = "{proc.display}"')
        lines.append(f'description = "{proc.description}"')
        lines.append(f'grep = "{proc.grep}"')
        lines.append(f'start_cmd = "{proc.start_cmd}"')
        lines.append("")

    for name, prof in config.profiles.items():
        qname = f'"{name}"' if " " in name or "+" in name else name
        lines.append(f"[profile.{qname}]")
        lines.append(f'description = "{prof.description}"')
        lines.append(f'color = "{prof.color}"')
        if prof.builtin:
            lines.append("builtin = true")
        lines.append("")

        lines.append(f"[profile.{qname}.services]")
        for svc_name, val in prof.services.items():
            lines.append(f'"{svc_name}" = {"true" if val else "false"}')
        lines.append("")

        lines.append(f"[profile.{qname}.processes]")
        for proc_id, val in prof.processes.items():
            lines.append(f'{proc_id} = {"true" if val else "false"}')
        lines.append("")

        lines.append(f"[profile.{qname}.tweaks]")
        lines.append(f"swappiness = {prof.tweaks.swappiness}")
        lines.append(f'compositor_unredirect = {"true" if prof.tweaks.compositor_unredirect else "false"}')
        lines.append(f'gpu_performance = {"true" if prof.tweaks.gpu_performance else "false"}')
        lines.append("")

    config.config_path.write_text("\n".join(lines), encoding="utf-8")
