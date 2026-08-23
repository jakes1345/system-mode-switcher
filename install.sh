#!/bin/bash
set -e

APP_DIR="/opt/obsidian-citadel"
DESKTOP_FILE="/usr/share/applications/obsidian-citadel.desktop"
ICON_FILE="/usr/share/icons/hicolor/scalable/apps/obsidian-citadel.svg"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 🛡️ Obsidian Citadel — Installer ==="

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo bash "$0" "$@"
fi

# Get the actual user (not root)
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")

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

# Config
echo "[4/4] Setting up config..."
CONFIG_SRC="$REAL_HOME/obsidian-citadel.toml"
# Migrate old config if present
OLD_CONFIG="$REAL_HOME/system-mode-switcher.toml"
if [ -f "$OLD_CONFIG" ] && [ ! -f "$CONFIG_SRC" ]; then
    echo "  Migrating config from $OLD_CONFIG -> $CONFIG_SRC"
    cp "$OLD_CONFIG" "$CONFIG_SRC"
elif [ -f "$CONFIG_SRC" ]; then
    echo "  Config already exists at $CONFIG_SRC — keeping it."
else
    echo "  No config found. App will use built-in defaults."
fi

echo ""
echo "=== ✅ Installation complete! ==="
echo "Launch 'Obsidian Citadel' from your application menu."
echo "Or run: python3 $APP_DIR/main.py"
