#!/usr/bin/env bash

echo "Installing Obsidian Citadel OS Orchestrator..."

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./install_service.sh)"
  exit 1
fi

cp obsidian-citadel.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now obsidian-citadel.service

echo "Obsidian Citadel Kernel Daemon is now running as ROOT on boot!"
echo "Check status with: systemctl status obsidian-citadel.service"
