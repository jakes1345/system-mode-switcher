#!/bin/bash
# 🏰 OBSIDIAN CITADEL — ENTERPRISE DEPLOYMENT PROTOCOL
# Kept for compatibility: the hub now runs from a root-owned copy in
# /opt/obsidian-citadel, which install.sh creates (code, venv, unit, polkit).

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
exec sudo bash "$PROJECT_ROOT/install.sh"
