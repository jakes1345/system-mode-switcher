#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Installing Citadel PolKit Policy..."
sudo install -m 644 -o root -g root internal/security/com.obsidian.citadel.policy /usr/share/polkit-1/actions/

echo "Installing Citadel Apply wrapper..."
sudo install -m 755 -o root -g root citadel-apply /usr/local/bin/citadel-apply

echo "PolKit configuration installed successfully!"
