<p align="center">
  <img src="assets/icon.png" alt="Obsidian Citadel icon" width="96">
</p>

<h1 align="center">Obsidian Citadel</h1>

<p align="center">
  Switch a Linux workstation between work modes in one click.
</p>

---

One Linux machine often does several jobs: gaming, web development, running local AI models, a security lab. Each job wants different things running and different kernel settings. Obsidian Citadel stores each job as a **profile**: which systemd services and background processes should run, and how the CPU, GPU, memory and audio should be tuned. Applying a profile makes the machine match it, and keeps it that way.

It is built for, and used daily on, my own workstation. The default service list, process list and Docker Compose paths in [`switcher/config.py`](switcher/config.py) describe that machine. To match yours, list your services and processes in `/etc/obsidian-citadel/citadel.toml` (see [Security](#security)) and edit the profiles in the dashboard or `~/obsidian-citadel.toml`.

## How it works

```
 GTK dashboard ─┐
 tray icon ─────┼── gRPC (unix socket) ──▶ citadel-hub (root, systemd)
 citadel_cli ───┘                             │
                                              ├─ reconciler: applies a profile once, then corrects drift every 10 s
                                              └─ builds a bash script and runs it as root
```

- **Hub** ([`services/hub/`](services/hub/)): a root daemon run by systemd ([`citadel-hub.service`](internal/systemd/citadel-hub.service)). It serves `SetProfile`, `GetCurrentState` and `StreamTelemetry` ([`citadel.proto`](internal/protocol/citadel.proto)) on the unix socket `/run/citadel/hub.sock`. `SetProfile` returns once the change has run, with its real result.
- **Reconciler** ([`reconciler.py`](services/hub/reconciler.py)): applies a profile in full once, when you switch to it. After that it checks services and processes every 10 seconds and corrects only what has drifted, so a service you stop by hand comes back. Anything still drifting after 3 corrections is logged and left alone until the profile is applied again.
- **Dashboard** ([`switcher/ui/`](switcher/ui/)): an unprivileged GTK 3 app. It edits profiles and toggles services and processes; Apply sends the switches exactly as they are set. It also shows live CPU, GPU, RAM and network usage streamed from the hub.
- **Tray icon** ([`citadel_tray.py`](citadel_tray.py)) and **CLI** ([`citadel_cli.py`](citadel_cli.py)): quick switching without opening the dashboard.

## Profiles

Five profiles are built in. Every one can be edited, and you can add your own.

| Profile | Runs | Tuning |
|---|---|---|
| **Gaming** | Only what a game needs: Docker, databases and web servers are stopped | `performance` CPU governor, CPU cores reserved for the game, swappiness 10, THP off, AMD GPU forced to its high performance level, higher PipeWire priority |
| **Programming** | Docker, PostgreSQL, MySQL, Nginx, PHP-FPM, Samba, Cloudflare Tunnel | Balanced defaults |
| **AI + Dev** | The Programming stack plus Ollama, a Qdrant vector database and a local AI assistant stack | THP `madvise` |
| **Red Team** | Fail2Ban, Snort, Tor and an OWASP Juice Shop lab | Stealth: all TCP and DNS routed through Tor, SSH port closed, Wi-Fi MAC randomized, Bluetooth blocked, page caches dropped and swap cycled on apply |
| **Game Dev** | MySQL, Nginx and Samba for sharing builds | Light background load |

## What a profile controls

- **Services:** start, stop or freeze (`systemctl freeze`) any systemd unit. A stopped service and its socket, path or timer triggers are masked until reboot (`systemctl mask --runtime`), so nothing can quietly start it again; switching to a profile that wants it lifts the mask.
- **Processes:** start, kill, or freeze in a cgroup v2 freezer (`/sys/fs/cgroup/citadel_cryo_*`). A frozen process keeps its memory but gets no CPU, and thaws instantly when you switch back. Docker Compose stacks are recognised by container name.
- **CPU:** scaling governor and energy-performance preference, plus reserving the last two cores for the game while system tasks are kept off them.
- **Memory:** swappiness, transparent huge pages, `vm.dirty_ratio` and `vm.dirty_background_ratio`.
- **GPU:** the vendor is detected automatically for live telemetry: `nvidia-smi` on NVIDIA, [LACT](https://github.com/ilya-zlobintsev/LACT) on AMD. On AMD, a profile can force the DPM performance level to `high`. A profile's GPU power limit is applied on switch (reset to the card default when unset), and the dashboard sets NVIDIA performance mode for your session after a successful apply.
- **Audio:** raises PipeWire and WirePlumber scheduling priority for lower latency while gaming.
- **Network:** transparent Tor routing, SSH lockout, MAC randomization and Bluetooth blocking (Red Team).

### Plugin hooks

The hooks are grouped by area in [`switcher/plugins/`](switcher/plugins/). About half of them change the system today. The rest only log a line until they're implemented. [`TODO.MD`](TODO.MD) is the roadmap for them.

## Requirements

- Linux with systemd and cgroups v2
- Python 3.11 or later, PyGObject with GTK 3, and Ayatana AppIndicator for the tray icon
- `grpcio`, `protobuf` and `psutil` ([`requirements-hub.txt`](requirements-hub.txt)); `install.sh` installs them into a virtualenv, which needs `python3-venv`
- Optional: `nvidia-smi` or `lact` for GPU control, NetworkManager for MAC randomization, Tor for the Red Team profile

## Installing

```bash
git clone https://github.com/jakes1345/system-mode-switcher.git
cd system-mode-switcher
sudo ./install.sh
```

`install.sh` copies the app to `/opt/obsidian-citadel`, owned by root, with its own virtualenv for `grpcio`, `protobuf` and `psutil` (GTK and PyGObject come from your distribution). It installs the desktop entry, icons and PolicyKit policy, fills in your user name in [`citadel-hub.service`](internal/systemd/citadel-hub.service), and enables and starts the hub. Launch **Obsidian Citadel** from your app menu.

The hub runs that copy, not your checkout: re-run `sudo ./install.sh` after changing the source. Hub logs go to `/var/log/obsidian-citadel/citadel.log`.

For Debian and Ubuntu, `./build_deb.sh` builds a `.deb` package instead.

### Running from source

```bash
pip install -r requirements-hub.txt
sudo CITADEL_USER=$USER CITADEL_CONFIG=$HOME/obsidian-citadel.toml python3 services/hub/main.py
python3 main.py                       # the dashboard, in another terminal
```

`CITADEL_USER` decides who may connect to the hub's socket; without it only root can.

## Command line

```bash
python3 citadel_cli.py status         # active profile and system state
python3 citadel_cli.py set Gaming     # switch profile
python3 citadel_cli.py monitor        # live telemetry
```

## Security

- **The hub listens only on a unix socket**, `/run/citadel/hub.sock`, owned by the user named in `CITADEL_USER` with mode `0600`. There is no TCP port: other machines and other local users can't reach it.
- **Commands come only from root-owned config.** The services and processes a profile may manage, including every `start_cmd` and `stop_cmd`, come from `/etc/obsidian-citadel/citadel.toml` (same TOML format, `[[service]]` and `[[process]]` tables) or the built-in defaults. That file and its directories must be owned by root and not group- or world-writable, or the hub refuses it. Your `~/obsidian-citadel.toml` and the dashboard only supply profile values: on/off for known services and processes, and checked tweak values.
- **The hub runs root-owned code.** It runs from `/opt/obsidian-citadel` with its own virtualenv in Python isolated mode (`-I`), so nothing your user can edit is imported as root.
- **Applying changes as root outside the hub needs your password.** When the dashboard isn't running as root, it applies changes through `pkexec /usr/local/bin/citadel-apply`. The PolicyKit policy ([`com.obsidian.citadel.policy`](internal/security/com.obsidian.citadel.policy)) requires an administrator password for that, cached for a few minutes (`auth_admin_keep`), and the wrapper only runs a private root-owned copy of a script owned by the user who authenticated.

## Tests

```bash
python3 -m unittest discover tests
```
