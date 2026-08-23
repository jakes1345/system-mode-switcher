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
Edit `~/.config/obsidian-citadel.toml` or use the GTK Dashboard to tweak your profiles.
The "Apply" action uses `pkexec` securely through a whitelisted PolicyKit wrapper.
