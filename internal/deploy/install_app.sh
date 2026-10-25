#!/bin/bash
# Copy the application into APP_DIR and give it its own Python environment.
#
#   install_app.sh <source checkout> <app dir>
#
# Run as root (install.sh does), everything under APP_DIR ends up root-owned and
# not group/world-writable: the hub runs this code as root, so the desktop user
# must not be able to edit it or its dependencies.
set -euo pipefail

SRC="$1"
APP_DIR="$2"

mkdir -p "$APP_DIR"
# Replace the code but keep venv/ (rebuilding it means re-downloading wheels)
rm -rf "$APP_DIR"/switcher "$APP_DIR"/services "$APP_DIR"/pkg "$APP_DIR"/internal \
       "$APP_DIR"/main.py "$APP_DIR"/citadel_cli.py "$APP_DIR"/citadel_tray.py "$APP_DIR"/requirements-hub.txt
cp -r "$SRC/switcher" "$SRC/services" "$APP_DIR/"
for d in pkg internal; do
    [ -d "$SRC/$d" ] && cp -r "$SRC/$d" "$APP_DIR/"
done
cp "$SRC/main.py" "$SRC/requirements-hub.txt" "$APP_DIR/"
for f in citadel_cli.py citadel_tray.py; do
    [ -f "$SRC/$f" ] && cp "$SRC/$f" "$APP_DIR/"
done
find "$APP_DIR" -path "$APP_DIR/venv" -prune -o -name __pycache__ -prune -exec rm -rf {} +

# System site-packages stay visible so the dashboard can import PyGObject (gi);
# grpcio/protobuf/psutil come from the venv. The hub runs with `python -I`, so
# no user site-packages or PYTHON* variables ever reach it.
if [ ! -x "$APP_DIR/venv/bin/python" ]; then
    python3 -m venv --system-site-packages "$APP_DIR/venv" || {
        echo "Could not create a virtualenv. Install python3-venv (apt install python3-venv) and retry." >&2
        exit 1
    }
fi
# --ignore-installed: the hub's own copies, even if /usr/local already satisfies them
"$APP_DIR/venv/bin/python" -m pip install --disable-pip-version-check --quiet --no-warn-conflicts --ignore-installed \
    -r "$APP_DIR/requirements-hub.txt"

if [ "$(id -u)" -eq 0 ]; then
    chown -R root:root "$APP_DIR"
fi
chmod -R go-w "$APP_DIR"
