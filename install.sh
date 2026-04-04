#!/bin/bash
set -e

APP_DIR="/opt/system-mode-switcher"
DESKTOP_FILE="/usr/share/applications/system-mode-switcher.desktop"
ICON_FILE="/usr/share/icons/hicolor/scalable/apps/system-mode-switcher.svg"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== System Mode Switcher — Installer ==="

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

# Copy desktop file
echo "[2/4] Installing desktop entry..."
cp "$SCRIPT_DIR/switcher/desktop/system-mode-switcher.desktop" "$DESKTOP_FILE"
# Update Exec path
sed -i "s|Exec=.*|Exec=python3 $APP_DIR/switcher/__main__.py|" "$DESKTOP_FILE"

# Copy icon
echo "[3/4] Installing icon..."
cp "$SCRIPT_DIR/switcher/desktop/system-mode-switcher.svg" "$ICON_FILE"
gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true

# Config
echo "[4/4] Setting up config..."
CONFIG_SRC="$REAL_HOME/system-mode-switcher.toml"
if [ -f "$CONFIG_SRC" ]; then
    echo "  Config already exists at $CONFIG_SRC — keeping it."
else
    echo "  No config found. App will use built-in defaults."
fi

echo ""
echo "=== Installation complete! ==="
echo "Launch from your application menu or run:"
echo "  python3 $APP_DIR/switcher/__main__.py"
