#!/bin/bash
# 🏰 OBSIDIAN CITADEL — DEBIAN PACKAGE BUILDER (.deb)
# Generates obsidian-citadel_1.0.0_amd64.deb for Debian/Ubuntu/Linux Mint distribution.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build_deb_tmp"
PKG_NAME="obsidian-citadel_1.0.0_amd64"
PKG_ROOT="$BUILD_DIR/$PKG_NAME"

echo "═══════════════════════════════════════════════════════════════"
echo "  🏰  OBSIDIAN CITADEL — BUILDING DEBIAN PACKAGE v1.0.0"
echo "═══════════════════════════════════════════════════════════════"

rm -rf "$BUILD_DIR"
mkdir -p "$PKG_ROOT/DEBIAN"
mkdir -p "$PKG_ROOT/opt/obsidian-citadel"
mkdir -p "$PKG_ROOT/usr/bin"
mkdir -p "$PKG_ROOT/usr/local/bin"
mkdir -p "$PKG_ROOT/etc/systemd/system"
mkdir -p "$PKG_ROOT/usr/share/polkit-1/actions"
mkdir -p "$PKG_ROOT/usr/share/applications"

# Copy application files into /opt/obsidian-citadel
echo "[1/5] Copying core application files..."
cp -r "$SCRIPT_DIR/switcher" "$PKG_ROOT/opt/obsidian-citadel/"
cp -r "$SCRIPT_DIR/services" "$PKG_ROOT/opt/obsidian-citadel/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/pkg" "$PKG_ROOT/opt/obsidian-citadel/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/internal" "$PKG_ROOT/opt/obsidian-citadel/" 2>/dev/null || true
cp "$SCRIPT_DIR/main.py" "$PKG_ROOT/opt/obsidian-citadel/"
cp "$SCRIPT_DIR/citadel_cli.py" "$PKG_ROOT/opt/obsidian-citadel/" 2>/dev/null || true
cp "$SCRIPT_DIR/citadel_tray.py" "$PKG_ROOT/opt/obsidian-citadel/" 2>/dev/null || true
cp "$SCRIPT_DIR/requirements-hub.txt" "$PKG_ROOT/opt/obsidian-citadel/"
find "$PKG_ROOT/opt/obsidian-citadel" -name __pycache__ -prune -exec rm -rf {} +

# Copy Systemd, Polkit, and Executables
echo "[2/5] Copying system services and security wrappers..."
cp "$SCRIPT_DIR/internal/systemd/citadel-hub.service" "$PKG_ROOT/etc/systemd/system/"
cp "$SCRIPT_DIR/internal/security/com.obsidian.citadel.policy" "$PKG_ROOT/usr/share/polkit-1/actions/"
cp "$SCRIPT_DIR/citadel-apply" "$PKG_ROOT/usr/local/bin/citadel-apply"
chmod 755 "$PKG_ROOT/usr/local/bin/citadel-apply"

# CLI wrappers in /usr/bin/
cat << 'EOF' > "$PKG_ROOT/usr/bin/obsidian-citadel"
#!/bin/sh
exec /opt/obsidian-citadel/venv/bin/python /opt/obsidian-citadel/main.py "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/obsidian-citadel"

cat << 'EOF' > "$PKG_ROOT/usr/bin/obsidian-citadel-cli"
#!/bin/sh
exec /opt/obsidian-citadel/venv/bin/python /opt/obsidian-citadel/citadel_cli.py "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/obsidian-citadel-cli"

cat << 'EOF' > "$PKG_ROOT/usr/bin/obsidian-citadel-tray"
#!/bin/sh
exec /opt/obsidian-citadel/venv/bin/python /opt/obsidian-citadel/citadel_tray.py "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/obsidian-citadel-tray"

# Desktop entry
echo "[3/5] Setting up desktop integration..."
cp "$SCRIPT_DIR/switcher/desktop/system-mode-switcher.desktop" "$PKG_ROOT/usr/share/applications/obsidian-citadel.desktop"
sed -i "s|Exec=.*|Exec=/usr/bin/obsidian-citadel|" "$PKG_ROOT/usr/share/applications/obsidian-citadel.desktop"

# Icons across standard sizes
sizes="16 24 32 48 64 128 256 512"
ICON_SRC="$SCRIPT_DIR/assets/icon.png"
if [ -f "$ICON_SRC" ]; then
    for s in $sizes; do
        mkdir -p "$PKG_ROOT/usr/share/icons/hicolor/${s}x${s}/apps"
        if [ -f "/tmp/citadel-${s}.png" ]; then
            cp "/tmp/citadel-${s}.png" "$PKG_ROOT/usr/share/icons/hicolor/${s}x${s}/apps/obsidian-citadel.png"
        else
            cp "$ICON_SRC" "$PKG_ROOT/usr/share/icons/hicolor/${s}x${s}/apps/obsidian-citadel.png"
        fi
    done
fi

# Package control file
echo "[4/5] Creating DEBIAN package control metadata..."
cat << 'EOF' > "$PKG_ROOT/DEBIAN/control"
Package: obsidian-citadel
Version: 1.0.0
Section: admin
Priority: optional
Architecture: amd64
Maintainer: Jack <jack@phaze.world>
Depends: python3 (>= 3.11), python3-venv, python3-gi, python3-pil, gir1.2-gtk-3.0
Recommends: gir1.2-ayatanaappindicator3-0.1, pipewire, lact
Description: Enterprise Workstation Mode Switcher & Control Plane
 Obsidian Citadel automatically orchestrates CPU governors, GPU power limits,
 systemd services, and Docker Compose stacks across Gaming, Programming,
 AI+Dev, Red Team, and Game Dev profiles.
EOF

# Post-install script
cat << 'EOF' > "$PKG_ROOT/DEBIAN/postinst"
#!/bin/sh
set -e
# grpcio/protobuf from distro packages are too old for the generated stubs, so the
# hub gets its own root-owned venv (see requirements-hub.txt)
APP=/opt/obsidian-citadel
[ -x "$APP/venv/bin/python" ] || python3 -m venv --system-site-packages "$APP/venv"
"$APP/venv/bin/python" -m pip install --disable-pip-version-check --quiet --no-warn-conflicts --ignore-installed -r "$APP/requirements-hub.txt"
chmod -R go-w "$APP"
if [ -n "$SUDO_USER" ]; then
    home=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    sed -i -e "s|CITADEL_CONFIG=.*\"|CITADEL_CONFIG=$home/obsidian-citadel.toml\"|" \
           -e "s|CITADEL_USER=.*\"|CITADEL_USER=$SUDO_USER\"|" /etc/systemd/system/citadel-hub.service
else
    echo "Set CITADEL_USER/CITADEL_CONFIG in /etc/systemd/system/citadel-hub.service for your desktop user."
fi
systemctl daemon-reload || true
systemctl enable citadel-hub.service || true
systemctl restart citadel-hub.service || true
update-desktop-database || true
gtk-update-icon-cache /usr/share/icons/hicolor/ || true
echo "🏰 Obsidian Citadel successfully installed and control plane service started."
EOF
chmod 755 "$PKG_ROOT/DEBIAN/postinst"

# The venv isn't tracked by dpkg, so remove it ourselves
cat << 'EOF' > "$PKG_ROOT/DEBIAN/postrm"
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    rm -rf /opt/obsidian-citadel/venv
fi
EOF
chmod 755 "$PKG_ROOT/DEBIAN/postrm"

# Build DEB
echo "[5/5] Building package file..."
dpkg-deb --build "$PKG_ROOT" "$SCRIPT_DIR/$PKG_NAME.deb"
rm -rf "$BUILD_DIR"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ SUCCESS: Package built at:"
echo "     $SCRIPT_DIR/$PKG_NAME.deb"
echo ""
echo "  To test install:"
echo "     sudo dpkg -i $SCRIPT_DIR/$PKG_NAME.deb"
echo "═══════════════════════════════════════════════════════════════"
