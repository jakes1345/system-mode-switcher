# 🏰 Obsidian Citadel — Release & Packaging Guide

This guide explains how to package, test, and release **Obsidian Citadel** for open-source distribution on Linux.

---

## 📦 1. Building the Debian/Ubuntu Package (`.deb`)

To build the standalone `.deb` package for Ubuntu, Linux Mint, Debian, and popOS:

```bash
chmod +x build_deb.sh
./build_deb.sh
```

This creates:
```
obsidian-citadel_1.0.0_amd64.deb
```

### Installation Test
To test installing the generated package:
```bash
sudo dpkg -i obsidian-citadel_1.0.0_amd64.deb
sudo apt-get install -f  # resolves dependencies automatically
```

---

## 🌐 2. One-Line Web Installer (`curl | bash`)

Users can install Citadel on **any Linux distro** in a single command:

```bash
curl -fsSL https://github.com/jakes1345/system-mode-switcher/raw/master/install.sh | sudo bash
```

### What `install.sh` Does:
1. Detects system package manager (`apt`, `pacman`, `dnf`, `zypper`).
2. Installs required system dependencies (`python3-gi`, `gir1.2-gtk-3.0`, `python3-grpc`, `python3-psutil`).
3. Installs Citadel into `/opt/obsidian-citadel/`.
4. Registers systemd service (`citadel-hub.service`) and Polkit rules (`/usr/local/bin/citadel-apply`).
5. Installs desktop entry and high-resolution icons (`16x16` to `512x512`).

---

## 🏷️ 3. Publishing a GitHub Release

1. **Tag the Release**:
   ```bash
   git add .
   git commit -m "release: Obsidian Citadel v1.0.0 — System Mode Switcher & Control Plane"
   git tag -a v1.0.0 -m "Obsidian Citadel v1.0.0 Initial Release"
   git push origin main --tags
   ```

2. **Create GitHub Release**:
   - Navigate to `https://github.com/jakes1345/system-mode-switcher/releases/new`.
   - Select tag `v1.0.0`.
   - Title: `Obsidian Citadel v1.0.0 — System Mode Switcher & Control Plane`.
   - Attach binary asset: `obsidian-citadel_1.0.0_amd64.deb`.
   - Paste release notes below.

---

## 📝 Release Notes Template

```markdown
# 🏰 Obsidian Citadel v1.0.0

Enterprise Workstation Mode Switcher & Control Plane for Linux.

### Key Features
- 🎮 **Gaming Mode**: Performance CPU governor (4.2 GHz), THP disabled, low-latency Pipewire audio, kills non-essential Docker/DBs (~2 GB RAM freed).
- 💻 **Programming Mode**: Docker, PostgreSQL 16, MySQL, Nginx, PHP-FPM, Samba, Cloudflare Tunnel.
- 🧠 **AI + Dev Mode**: Ollama LLM + Friday AI stack (Open WebUI + Brain + Qdrant) + Friday Hands + THP madvise.
- 🔴 **Red Team Mode**: Stealth networking, Tor, Fail2Ban, Snort, Battleground Lab (Juice Shop), MAC randomization, RAM wipe on exit.
- 🎨 **Game Dev Mode**: Lean mode for Godot/Unity with MySQL, Nginx, and Samba file sharing.

### Quick Install

**Ubuntu / Debian / Linux Mint (.deb)**:
```bash
wget https://github.com/jakes1345/system-mode-switcher/releases/download/v1.0.0/obsidian-citadel_1.0.0_amd64.deb
sudo dpkg -i obsidian-citadel_1.0.0_amd64.deb
sudo apt-get install -f
```

**Universal One-Liner (Any Linux Distro)**:
```bash
curl -fsSL https://raw.githubusercontent.com/jakes1345/system-mode-switcher/main/install.sh | bash
```
```
