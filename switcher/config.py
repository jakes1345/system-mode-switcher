"""TOML configuration loader and saver with validation."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path



@dataclass
class ServiceConfig:
    name: str          # systemd unit name
    display: str       # human-readable label
    description: str   # short description
    category: str = "System"


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
    cpu_governor: str = "schedutil"
    gpu_power_limit: int | None = None
    thp_mode: str = "madvise"
    stealth_mode: bool = False
    gaming_audio: bool = False
    cpu_shielding: bool = False
    clear_ram_on_exit: bool = False
    dirty_ratio: int = 20
    dirty_background_ratio: int = 10


@dataclass
class ProfileConfig:
    name: str
    description: str = ""
    color: str = "#4fc3f7"
    icon: str = "⚙️"  # emoji identity for this mode
    activation_message: str = ""  # detailed notification on apply
    builtin: bool = False
    services: dict[str, bool] = field(default_factory=dict)
    processes: dict[str, bool] = field(default_factory=dict)
    tweaks: TweakConfig = field(default_factory=TweakConfig)


@dataclass
class Config:
    services: list[ServiceConfig] = field(default_factory=list)
    processes: list[ProcessConfig] = field(default_factory=list)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    config_path: Path = field(default_factory=lambda: Path.home() / "obsidian-citadel.toml")
    load_error: str | None = None


# ── Built-in defaults ────────────────────────────────────────────────────

DEFAULT_SERVICES = [
    ServiceConfig("fail2ban.service", "Fail2Ban", "Intrusion prevention daemon", "Security"),
    ServiceConfig("snort.service", "Snort", "Network IDS/IPS engine", "Security"),
    ServiceConfig("openvpn.service", "OpenVPN", "VPN tunnel daemon", "Network"),
    ServiceConfig("mysql.service", "MySQL", "Relational database server", "Data & AI"),
    ServiceConfig("postgresql@16-main.service", "PostgreSQL", "Database server", "Data & AI"),
    ServiceConfig("docker.service", "Docker", "Container engine daemon", "Virtualization"),
    ServiceConfig("containerd.service", "Containerd", "Container runtime engine", "Virtualization"),
    ServiceConfig("nginx.service", "Nginx", "HTTP/HTTPS web server & dev proxy", "Network"),
    ServiceConfig("cloudflared.service", "Cloudflare Tunnel", "Exposes local web services securely", "Network"),
    ServiceConfig("avahi-daemon.service", "Avahi mDNS", "Zero-configuration network discovery", "Network"),
    ServiceConfig("php8.3-fpm.service", "PHP-FPM", "PHP FastCGI process manager", "System"),
    ServiceConfig("postfix@-.service", "Postfix", "Mail transfer agent", "Network"),
    ServiceConfig("smbd.service", "Samba (SMB)", "SMB network file sharing", "Network"),
    ServiceConfig("nmbd.service", "Samba (NMB)", "NetBIOS name server", "Network"),
    ServiceConfig("tor@default.service", "Tor", "Anonymizing overlay network", "Security"),
    ServiceConfig("shadow-cypher.service", "ShadowCypher", "Tactical router panel", "Security"),
    ServiceConfig("cups.service", "CUPS", "Print spooler service", "System"),
    ServiceConfig("cups-browsed.service", "CUPS Browsed", "Printer discovery daemon", "System"),
    ServiceConfig("tailscaled.service", "Tailscale", "Mesh VPN daemon", "Network"),
    ServiceConfig("bluetooth.service", "Bluetooth", "Bluetooth service daemon", "System"),
    ServiceConfig("ModemManager.service", "ModemManager", "Cellular modem daemon", "Network"),
    ServiceConfig("lactd.service", "LACT", "GPU control & power daemon", "System"),
    ServiceConfig("ollama.service", "Ollama", "Local LLM runner daemon", "Data & AI"),
]

DEFAULT_PROCESSES = [
    ProcessConfig("qdrant", "Qdrant Vector DB", "Standalone vector database", "qdrant",
                  "qdrant --config-path /etc/qdrant/config.yaml"),
    ProcessConfig("shadow-sentinel", "Sentinel AI", "Headless Recon Bot", "shadowcypher.core.irc_bot",
                  "python3 -m shadowcypher.core.irc_bot"),
    ProcessConfig("shadow-hub", "ShadowHub", "Core Tactical Backend", "shadowcypher.core.hub",
                  "python3 -m shadowcypher.core.hub"),
    ProcessConfig("friday-hands", "Friday Hands", "AI agent execution server", "friday_hands|8102",
                  "systemctl start friday-hands 2>/dev/null || true"),
    ProcessConfig("compose-friday-ai", "Friday AI Stack", "Open WebUI + Brain + Qdrant (Docker)", "friday-webui|friday-brain",
                  "docker compose -f '/media/jack/New Volume/FRIDAY_AI/docker-compose.yml' up -d"),
    ProcessConfig("compose-poi", "POI OSINT Stack", "Search & OSINT stack (Docker)", "poi-api|poi-worker|poi-beat",
                  "docker compose -f '/media/jack/New Volume/POI/docker-compose.yml' up -d 2>/dev/null || docker compose -f '/home/jack/POI/docker-compose.yml' up -d"),
    ProcessConfig("compose-battleground", "Battleground Lab", "OWASP Juice Shop lab (Docker)", "battleground-juice-shop",
                  "docker compose -f '/home/jack/ShadowCypher/shadowcypher/battleground/docker-compose.yml' up -d"),
    ProcessConfig("compose-plandex", "Plandex AI Stack", "Plandex AI Postgres DB (Docker)", "app-plandex-postgres",
                  "docker compose -f '/home/jack/plandex-cli-v2.2.1/app/docker-compose.yml' up -d"),
]

_ALL_OFF = {s.name: False for s in DEFAULT_SERVICES}
_KEEP_ON = {
    "bluetooth.service": True,
    "lactd.service": True,
    "cloudflared.service": True,
    "tailscaled.service": True,
}

_SVC_PROGRAMMING = {
    "fail2ban.service": False, "snort.service": False, "openvpn.service": False,
    "mysql.service": True, "postgresql@16-main.service": True,
    "docker.service": True, "containerd.service": True,
    "nginx.service": True, "cloudflared.service": True, "avahi-daemon.service": False,
    "php8.3-fpm.service": True, "postfix@-.service": False,
    "smbd.service": True, "nmbd.service": True,
    "tor@default.service": False, "shadow-cypher.service": True,
    "cups.service": True, "cups-browsed.service": True,
    "tailscaled.service": True, "bluetooth.service": True,
    "ModemManager.service": False, "lactd.service": True, "ollama.service": False,
}

DEFAULT_PROFILES: dict[str, ProfileConfig] = {
    "Gaming": ProfileConfig(
        name="Gaming",
        description="Maximum FPS. Kills everything non-essential (Docker, DBs, web servers).",
        color="#e74c3c", icon="🎮", builtin=True,
        activation_message=(
            "GAMING MODE ACTIVE\n\n"
            "• CPU Governor → PERFORMANCE (all 12 threads locked to 4.2 GHz)\n"
            "• Docker + Containerd + ALL Docker Stacks → TERMINATED (~2 GB RAM freed)\n"
            "• MySQL + PostgreSQL + Ollama → KILLED\n"
            "• Nginx + PHP-FPM + Postfix + Tor + Fail2Ban → KILLED\n"
            "• THP → DISABLED (zero compaction latency spikes)\n"
            "• Swappiness → 10 (minimal swap pressure)\n"
            "• Pipewire low-latency audio boosted\n"
            "• LACT GPU control + Bluetooth + Cloudflare Tunnel → KEPT"
        ),
        services={**_ALL_OFF, **_KEEP_ON},
        processes={
            "qdrant": False,
            "shadow-sentinel": False,
            "shadow-hub": False,
            "friday-hands": False,
            "compose-friday-ai": False,
            "compose-poi": False,
            "compose-battleground": False,
            "compose-plandex": False,
        },
        tweaks=TweakConfig(
            swappiness=10,
            compositor_unredirect=True,
            gpu_performance=True,
            cpu_governor="performance",
            thp_mode="never",
            dirty_ratio=5,
            dirty_background_ratio=2,
            gaming_audio=True,
            cpu_shielding=True,
        ),
    ),
    "Programming": ProfileConfig(
        name="Programming",
        description="Full dev stack. Docker, DBs, Nginx, Samba, Cloudflare. AI model off.",
        color="#2ecc71", icon="💻", builtin=True,
        activation_message=(
            "DEV MODE ACTIVE\n\n"
            "• Docker + Containerd → ON\n"
            "• Plandex DB stack → ONLINE\n"
            "• PostgreSQL 16 + MySQL → ON\n"
            "• Nginx (phaze.world/xat.dev) + PHP-FPM → ON\n"
            "• Cloudflare Tunnel + Samba → ON\n"
            "• ShadowCypher Panel → ON\n"
            "• Heavy AI stacks (Ollama/Friday AI) → OFF (saving RAM for builds)\n"
            "• CPU Governor → schedutil (balanced)\n"
            "• Swappiness → 30"
        ),
        services=dict(_SVC_PROGRAMMING),
        processes={
            "qdrant": False,
            "shadow-sentinel": False,
            "shadow-hub": False,
            "friday-hands": False,
            "compose-friday-ai": False,
            "compose-poi": False,
            "compose-battleground": False,
            "compose-plandex": True,
        },
        tweaks=TweakConfig(swappiness=30),
    ),
    "AI + Dev": ProfileConfig(
        name="AI + Dev",
        description="LLM + Friday AI stack + Vector DB + full dev stack online.",
        color="#9b59b6", icon="🧠", builtin=True,
        activation_message=(
            "AI + DEV MODE ACTIVE\n\n"
            "• Ollama LLM Runner → ON\n"
            "• Friday AI stack (Open WebUI + Brain + Qdrant) → ONLINE\n"
            "• Friday Hands AI Agent Server → ONLINE\n"
            "• Docker + Plandex DB + PostgreSQL + MySQL → ON\n"
            "• Nginx + Cloudflare Tunnel → ON\n"
            "• THP → madvise (optimized for large model allocations)\n"
            "• CPU Governor → schedutil (balanced)\n"
            "• Swappiness → 30"
        ),
        services={**_SVC_PROGRAMMING, "ollama.service": True},
        processes={
            "qdrant": True,
            "shadow-sentinel": False,
            "shadow-hub": False,
            "friday-hands": True,
            "compose-friday-ai": True,
            "compose-poi": False,
            "compose-battleground": False,
            "compose-plandex": True,
        },
        tweaks=TweakConfig(swappiness=30, thp_mode="madvise"),
    ),
    "Red Team": ProfileConfig(
        name="Red Team",
        description="Offensive security lab. Stealth + IDS + Tor + Battleground lab.",
        color="#ff1744", icon="🔴", builtin=True,
        activation_message=(
            "RED TEAM MODE ACTIVE\n\n"
            "• Tor Anonymizing Network → ON\n"
            "• Fail2Ban Intrusion Prevention → ARMED\n"
            "• Snort Network IDS/IPS → ARMED\n"
            "• Shadow Sentinel + ShadowHub → DEPLOYED\n"
            "• Battleground Lab (Juice Shop) → ONLINE\n"
            "• MAC Address → RANDOMIZED\n"
            "• Bluetooth + Avahi → KILLED (stealth)\n"
            "• Cloudflare Tunnel → DISABLED (OPSEC protection)\n"
            "• Docker + Containerd → ON (lab infra)\n"
            "• Stealth Mode → ENABLED\n"
            "• RAM Wipe on Exit → ARMED"
        ),
        services={
            "fail2ban.service": True, "snort.service": True, "openvpn.service": False,
            "mysql.service": False, "postgresql@16-main.service": False,
            "docker.service": True, "containerd.service": True,
            "nginx.service": False, "cloudflared.service": False, "avahi-daemon.service": False,
            "php8.3-fpm.service": False, "postfix@-.service": False,
            "smbd.service": False, "nmbd.service": False,
            "tor@default.service": True, "shadow-cypher.service": False,
            "cups.service": False, "cups-browsed.service": False,
            "tailscaled.service": True, "bluetooth.service": False,
            "ModemManager.service": False, "lactd.service": True, "ollama.service": False,
        },
        processes={
            "qdrant": False,
            "shadow-sentinel": True,
            "shadow-hub": True,
            "friday-hands": False,
            "compose-friday-ai": False,
            "compose-poi": False,
            "compose-battleground": True,
            "compose-plandex": False,
        },
        tweaks=TweakConfig(swappiness=30, stealth_mode=True, clear_ram_on_exit=True),
    ),
    "Game Dev": ProfileConfig(
        name="Game Dev",
        description="MySQL + Nginx + Samba file sharing. Lean background.",
        color="#e67e22", icon="🎨", builtin=True,
        activation_message=(
            "GAME DEV MODE ACTIVE\n\n"
            "• MySQL → ON (game assets/user db)\n"
            "• Nginx → ON (preview builds)\n"
            "• Samba File Sharing → ON (asset sharing)\n"
            "• Docker / Containers → OFF (free resources)\n"
            "• PostgreSQL + Heavy AI → OFF\n"
            "• CPU Governor → schedutil (balanced)\n"
            "• Swappiness → 30"
        ),
        services={
            "fail2ban.service": False, "snort.service": False, "openvpn.service": False,
            "mysql.service": True, "postgresql@16-main.service": False,
            "docker.service": False, "containerd.service": False,
            "nginx.service": True, "cloudflared.service": False, "avahi-daemon.service": False,
            "php8.3-fpm.service": False, "postfix@-.service": False,
            "smbd.service": True, "nmbd.service": True,
            "tor@default.service": False, "shadow-cypher.service": False,
            "cups.service": False, "cups-browsed.service": False,
            "tailscaled.service": True, "bluetooth.service": True,
            "ModemManager.service": False, "lactd.service": True, "ollama.service": False,
        },
        processes={
            "qdrant": False,
            "shadow-sentinel": False,
            "shadow-hub": False,
            "friday-hands": False,
            "compose-friday-ai": False,
            "compose-poi": False,
            "compose-battleground": False,
            "compose-plandex": False,
        },
        tweaks=TweakConfig(swappiness=30),
    ),
}


def load_config(path: Path | None = None) -> Config:
    """Load config from TOML. Returns defaults on missing/malformed file."""
    config_path = path or Path.home() / "obsidian-citadel.toml"
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
    except (tomllib.TOMLDecodeError, OSError) as e:
        import sys
        print(f"WARNING: Failed to parse {config_path}: {e}. Using defaults.", file=sys.stderr)
        return Config(
            services=list(DEFAULT_SERVICES),
            processes=list(DEFAULT_PROCESSES),
            profiles=dict(DEFAULT_PROFILES),
            config_path=config_path,
            load_error=f"Failed to parse {config_path}: {e}",
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
                category=s.get("category", "System"),
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
                icon=pdata.get("icon", "⚙️"),
                activation_message=pdata.get("activation_message", ""),
                builtin=pdata.get("builtin", False),
                services={k: bool(v) for k, v in pdata.get("services", {}).items()},
                processes={k: bool(v) for k, v in pdata.get("processes", {}).items()},
                tweaks=TweakConfig(
                    swappiness=tweaks_raw.get("swappiness", 30),
                    compositor_unredirect=bool(tweaks_raw.get("compositor_unredirect", False)),
                    gpu_performance=bool(tweaks_raw.get("gpu_performance", False)),
                    cpu_governor=tweaks_raw.get("cpu_governor", "schedutil"),
                    gpu_power_limit=tweaks_raw.get("gpu_power_limit"),
                    thp_mode=tweaks_raw.get("thp_mode", "madvise"),
                    stealth_mode=bool(tweaks_raw.get("stealth_mode", False)),
                    gaming_audio=bool(tweaks_raw.get("gaming_audio", False)),
                    cpu_shielding=bool(tweaks_raw.get("cpu_shielding", False)),
                    clear_ram_on_exit=bool(tweaks_raw.get("clear_ram_on_exit", False)),
                    dirty_ratio=tweaks_raw.get("dirty_ratio", 20),
                    dirty_background_ratio=tweaks_raw.get("dirty_background_ratio", 10),
                ),
            )

    return config


def save_config(config: Config) -> None:
    """Write current config back to TOML."""
    lines: list[str] = [
        "# Obsidian Citadel — Configuration",
        "# Auto-generated. Edit with care.",
        "",
    ]

    for svc in config.services:
        lines.append("[[service]]")
        lines.append(f'name = "{svc.name}"')
        lines.append(f'display = "{svc.display}"')
        lines.append(f'description = "{svc.description}"')
        lines.append(f'category = "{svc.category}"')
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
        qname = f'"{name}"'
        lines.append(f"[profile.{qname}]")
        lines.append(f'description = "{prof.description}"')
        lines.append(f'color = "{prof.color}"')
        lines.append(f'icon = "{prof.icon}"')
        if prof.activation_message:
            # Escape newlines for TOML single-line string
            lines.append(f'activation_message = "{prof.activation_message.replace(chr(10), "\\n")}"')
        if prof.builtin:
            lines.append("builtin = true")
        lines.append("")

        lines.append(f"[profile.{qname}.services]")
        for svc_name, val in prof.services.items():
            lines.append(f'"{svc_name}" = {"true" if val else "false"}')
        lines.append("")

        lines.append(f"[profile.{qname}.processes]")
        for proc_id, val in prof.processes.items():
            lines.append(f'"{proc_id}" = {"true" if val else "false"}')
        lines.append("")

        lines.append(f"[profile.{qname}.tweaks]")
        lines.append(f"swappiness = {prof.tweaks.swappiness}")
        lines.append(f'compositor_unredirect = {"true" if prof.tweaks.compositor_unredirect else "false"}')
        lines.append(f'gpu_performance = {"true" if prof.tweaks.gpu_performance else "false"}')
        lines.append(f'cpu_governor = "{prof.tweaks.cpu_governor}"')
        if prof.tweaks.gpu_power_limit is not None:
            lines.append(f"gpu_power_limit = {prof.tweaks.gpu_power_limit}")
        lines.append(f'thp_mode = "{prof.tweaks.thp_mode}"')
        lines.append(f'stealth_mode = {"true" if prof.tweaks.stealth_mode else "false"}')
        lines.append(f'gaming_audio = {"true" if prof.tweaks.gaming_audio else "false"}')
        lines.append(f'cpu_shielding = {"true" if prof.tweaks.cpu_shielding else "false"}')
        lines.append(f'clear_ram_on_exit = {"true" if prof.tweaks.clear_ram_on_exit else "false"}')
        lines.append(f"dirty_ratio = {prof.tweaks.dirty_ratio}")
        lines.append(f"dirty_background_ratio = {prof.tweaks.dirty_background_ratio}")
        lines.append("")

    config.config_path.write_text("\n".join(lines), encoding="utf-8")
