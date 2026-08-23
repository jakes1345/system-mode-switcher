#!/bin/bash
# 🏰 OBSIDIAN CITADEL — ENTERPRISE DEPLOYMENT PROTOCOL
# Hardens and installs the control plane into the host OS.

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🛡️ Deploying Obsidian Citadel Security Policy..."
sudo cp "$PROJECT_ROOT/internal/security/com.obsidian.citadel.policy" /usr/share/polkit-1/actions/

echo "🔒 Installing PolicyKit wrapper..."
sudo cp "$PROJECT_ROOT/citadel-apply" /usr/local/bin/citadel-apply
sudo chmod 755 /usr/local/bin/citadel-apply

echo "🏗️ Installing Citadel Hub Control Plane Service..."
sudo cp "$PROJECT_ROOT/internal/systemd/citadel-hub.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable citadel-hub.service

echo "🖼️ Injecting Citadel Branding..."
sudo mkdir -p /usr/share/icons/hicolor/256x256/apps/

ICON_PATH=""
if [ -f "$PROJECT_ROOT/switcher/assets/citadel_icon.png" ]; then
    ICON_PATH="$PROJECT_ROOT/switcher/assets/citadel_icon.png"
elif [ -f "$PROJECT_ROOT/switcher/assets/citadel-apex.png" ]; then
    ICON_PATH="$PROJECT_ROOT/switcher/assets/citadel-apex.png"
fi

if [ -n "$ICON_PATH" ]; then
    sudo cp "$ICON_PATH" /usr/share/icons/hicolor/256x256/apps/obsidian-citadel.png
    echo "  [SUCCESS] High-fidelity icon cached at /usr/share/icons/..."
else
    echo "  [WARNING] Custom icon not found. Falling back to system default."
fi

echo "🖥️ Finalizing Desktop Entry..."
sudo cp "$PROJECT_ROOT/switcher/desktop/system-mode-switcher.desktop" /usr/share/applications/obsidian-citadel.desktop
sudo update-desktop-database

echo "✅ CITADEL DEPLOYMENT COMPLETE."
