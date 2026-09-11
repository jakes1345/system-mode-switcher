#!/bin/bash
set -e

APP_DIR="/opt/obsidian-citadel"
DESKTOP_FILE="/usr/share/applications/obsidian-citadel.desktop"
ICON_FILE="/usr/share/icons/hicolor/scalable/apps/obsidian-citadel.svg"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 🛡️ Obsidian Citadel — Installer ==="

# Check root elevation
if [ "$EUID" -ne 0 ]; then
    echo "=== 🛡️ Obsidian Citadel — Installer ==="
    echo "Root privileges are required to install Citadel system services."
    echo ""
    echo "Please run with sudo:"
    echo "  curl -fsSL https://github.com/jakes1345/system-mode-switcher/raw/master/install.sh | sudo bash"
    exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")"

# If run via curl pipe or SCRIPT_DIR doesn't have switcher/, fetch repository
if [ ! -d "$SCRIPT_DIR/switcher" ]; then
    echo "[0/4] Fetching latest Citadel release from GitHub..."
    TMP_REPO="/tmp/citadel-install-repo"
    rm -rf "$TMP_REPO"
    mkdir -p "$TMP_REPO"
    if command -v git >/dev/null 2>&1; then
        git clone --depth 1 https://github.com/jakes1345/system-mode-switcher.git "$TMP_REPO" 2>/dev/null
    fi
    if [ ! -d "$TMP_REPO/switcher" ]; then
        curl -fsSL https://github.com/jakes1345/system-mode-switcher/archive/refs/heads/master.tar.gz | tar -xz -C /tmp 2>/dev/null
        rm -rf "$TMP_REPO"
        mv /tmp/system-mode-switcher-master "$TMP_REPO"
    fi
    SCRIPT_DIR="$TMP_REPO"
fi

# Copy application
echo "[1/4] Installing application to $APP_DIR..."
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$SCRIPT_DIR/switcher" "$APP_DIR/"
cp -r "$SCRIPT_DIR/services" "$APP_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/pkg" "$APP_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/internal" "$APP_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/main.py" "$APP_DIR/"
cp "$SCRIPT_DIR/citadel_cli.py" "$APP_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/citadel_tray.py" "$APP_DIR/" 2>/dev/null || true

# Copy desktop file
echo "[2/4] Installing desktop entry..."
cp "$SCRIPT_DIR/switcher/desktop/system-mode-switcher.desktop" "$DESKTOP_FILE"
# Update Exec path for system-wide deploy
sed -i "s|Exec=.*|Exec=python3 $APP_DIR/main.py|" "$DESKTOP_FILE"

# Deploy icon — check project assets first
echo "[3/4] Installing icons..."
mkdir -p "$APP_DIR/switcher/assets"
ICON_SOURCE=""

# Priority 1: Project root assets directory
if [ -s "$SCRIPT_DIR/assets/icon.png" ]; then
    ICON_SOURCE="$SCRIPT_DIR/assets/icon.png"
elif [ -s "$SCRIPT_DIR/switcher/assets/citadel-apex.png" ]; then
    ICON_SOURCE="$SCRIPT_DIR/switcher/assets/citadel-apex.png"
elif [ -s "$SCRIPT_DIR/switcher/assets/citadel_icon.png" ]; then
    ICON_SOURCE="$SCRIPT_DIR/switcher/assets/citadel_icon.png"
fi

if [ -n "$ICON_SOURCE" ]; then
    echo "  Deploying icon: $ICON_SOURCE"
    cp "$ICON_SOURCE" "$APP_DIR/switcher/assets/citadel_icon.png"
    sed -i "s|Icon=.*|Icon=$APP_DIR/switcher/assets/citadel_icon.png|" "$DESKTOP_FILE"
else
    echo "  No custom icon found. Using system default."
    sed -i "s|Icon=.*|Icon=preferences-system|" "$DESKTOP_FILE"
fi

# SVG fallback for system icon cache
if [ -f "$SCRIPT_DIR/switcher/desktop/system-mode-switcher.svg" ]; then
    cp "$SCRIPT_DIR/switcher/desktop/system-mode-switcher.svg" "$ICON_FILE" 2>/dev/null || true
fi
gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true

# Security & Services
echo "[4/5] Deploying Polkit policy & Citadel control plane..."
mkdir -p /usr/share/polkit-1/actions/
cp "$SCRIPT_DIR/internal/security/com.obsidian.citadel.policy" /usr/share/polkit-1/actions/ 2>/dev/null || true
cp "$SCRIPT_DIR/citadel-apply" /usr/local/bin/citadel-apply
chmod 755 /usr/local/bin/citadel-apply

cp "$SCRIPT_DIR/internal/systemd/citadel-hub.service" /etc/systemd/system/ 2>/dev/null || true
systemctl daemon-reload 2>/dev/null || true
systemctl enable citadel-hub.service 2>/dev/null || true
systemctl restart citadel-hub.service 2>/dev/null || true

# Config
echo "[5/5] Setting up user configuration..."
CONFIG_SRC="$REAL_HOME/obsidian-citadel.toml"
OLD_CONFIG="$REAL_HOME/system-mode-switcher.toml"
if [ -f "$OLD_CONFIG" ] && [ ! -f "$CONFIG_SRC" ]; then
    echo "  Migrating config from $OLD_CONFIG -> $CONFIG_SRC"
    cp "$OLD_CONFIG" "$CONFIG_SRC"
elif [ -f "$CONFIG_SRC" ]; then
    echo "  Config already exists at $CONFIG_SRC — keeping it."
else
    echo "  No config found. App will use built-in defaults."
fi

# Cleanup temp repo if created
if [ -d "/tmp/citadel-install-repo" ]; then
    rm -rf /tmp/citadel-install-repo
fi

echo ""
echo "=== ✅ Obsidian Citadel Installation Complete! ==="
echo "Control plane active. Launch 'Obsidian Citadel' from your app menu."
echo "CLI command: python3 $APP_DIR/citadel_cli.py status"
