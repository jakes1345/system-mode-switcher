# 🏰 Obsidian Citadel (System Mode Switcher)

**Obsidian Citadel** is a Google-grade control plane for Linux. It transforms your Linux workstation between different hardware and software profiles (e.g., Gaming, Programming, Stealth, Performance) using a combination of systemd orchestration, kernel tuning, and dynamic hardware configuration.

## 🌟 Features
- **gRPC Control Plane**: The Hub daemon manages state reconciliation completely asynchronously.
- **10-Phase Execution Engine**: Hooks into kernel, Wayland, storage, and networking layers.
- **Zero-Copy Telemetry**: Live CPU, GPU, RAM, and Network monitoring in the dashboard.
- **Dynamic Cgroups v2 & Freezing**: Stops background tasks from stealing game frame times.
- **NVIDIA & AMD Support**: GPU vendor-aware power limit and fan curve tuning.

## 🏗️ Architecture

Obsidian Citadel is designed with a K8s-style reconciler architecture:
1. **The Hub (`citadel-hub.service`)**: A root-level daemon listening on gRPC.
2. **The Reconciler**: A loop running inside the Hub that prevents configuration drift.
3. **The UI**: A beautiful, unprivileged GTK3 dashboard that talks to the Hub over gRPC.

## 🚀 Installation
Run the deployment script to harden the application and install the systemd unit.
```bash
sudo ./install.sh
sudo ./deploy_citadel.sh
```

## 🛠️ Modifying Profiles
Edit `~/obsidian-citadel.toml` or use the GTK Dashboard to tweak your profiles.

## 🔐 Security Model
- The Hub listens only on the unix socket `/run/citadel/hub.sock`, owned by the
  desktop user named in `CITADEL_USER` (mode `0600`). There is no TCP port.
- The Hub reads **profile values only** from your `~/obsidian-citadel.toml`
  (on/off for known services and processes, validated tweak values).
- The services and processes it may manage — including every `start_cmd`/`stop_cmd`
  — come from the root-owned `/etc/obsidian-citadel/citadel.toml` (same TOML
  format, `[[service]]`/`[[process]]` tables), or the built-in defaults if it is
  absent. The file and its directories must be owned by root and not
  group/world-writable, or the Hub refuses it.
- The `citadel-apply` PolicyKit action requires an admin password
  (`auth_admin_keep`) and only runs a private root-owned copy of a script owned
  by the authenticating user.
