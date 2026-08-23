#!/bin/bash
set -e

echo "Installing Citadel PolKit Policy..."
sudo cp internal/security/com.obsidian.citadel.policy /usr/share/polkit-1/actions/
sudo chown root:root /usr/share/polkit-1/actions/com.obsidian.citadel.policy

echo "Creating Citadel Apply wrapper..."
cat << 'EOF' | sudo tee /usr/local/bin/citadel-apply > /dev/null
#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: citadel-apply <script.sh>"
    exit 1
fi
bash "$1"
EOF
sudo chmod +x /usr/local/bin/citadel-apply

echo "PolKit configuration installed successfully!"
