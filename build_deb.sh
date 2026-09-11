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

# Copy Systemd, Polkit, and Executables
echo "[2/5] Copying system services and security wrappers..."
cp "$SCRIPT_DIR/internal/systemd/citadel-hub.service" "$PKG_ROOT/etc/systemd/system/"
cp "$SCRIPT_DIR/internal/security/com.obsidian.citadel.policy" "$PKG_ROOT/usr/share/polkit-1/actions/"
cp "$SCRIPT_DIR/citadel-apply" "$PKG_ROOT/usr/local/bin/citadel-apply"
chmod 755 "$PKG_ROOT/usr/local/bin/citadel-apply"

# CLI wrappers in /usr/bin/
cat << 'EOF' > "$PKG_ROOT/usr/bin/obsidian-citadel"
#!/bin/sh
exec python3 /opt/obsidian-citadel/main.py "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/obsidian-citadel"

cat << 'EOF' > "$PKG_ROOT/usr/bin/obsidian-citadel-cli"
#!/bin/sh
exec python3 /opt/obsidian-citadel/citadel_cli.py "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/obsidian-citadel-cli"

cat << 'EOF' > "$PKG_ROOT/usr/bin/obsidian-citadel-tray"
#!/bin/sh
exec python3 /opt/obsidian-citadel/citadel_tray.py "$@"
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
Depends: python3, python3-gi, python3-psutil, python3-grpc, python3-pil, gir1.2-gtk-3.0
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
systemctl daemon-reload || true
systemctl enable citadel-hub.service || true
systemctl restart citadel-hub.service || true
update-desktop-database || true
gtk-update-icon-cache /usr/share/icons/hicolor/ || true
echo "🏰 Obsidian Citadel successfully installed and control plane service started."
EOF
chmod 755 "$PKG_ROOT/DEBIAN/postinst"

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
