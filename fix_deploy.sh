#!/bin/bash
# 🛡️ OBSIDIAN CITADEL — FIX DEPLOY SCRIPT
# Run this with: sudo bash /home/jack/system-mode-switcher/fix_deploy.sh
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  🛡️  OBSIDIAN CITADEL — MODE SWITCHER FIX DEPLOYMENT"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Step 1: Kill the duplicate service ──
echo "[1/5] Stopping and disabling duplicate 'obsidian-citadel.service'..."
systemctl stop obsidian-citadel.service 2>/dev/null || true
systemctl disable obsidian-citadel.service 2>/dev/null || true
rm -f /etc/systemd/system/obsidian-citadel.service
echo "  ✅ Duplicate service removed."
echo ""

# ── Step 2: Deploy the fixed citadel-hub.service ──
echo "[2/5] Installing fixed 'citadel-hub.service'..."
cp /home/jack/system-mode-switcher/internal/systemd/citadel-hub.service /etc/systemd/system/citadel-hub.service
echo "  ✅ Service file updated."
echo ""

# ── Step 3: Reload systemd and restart ──
echo "[3/5] Reloading systemd and restarting hub..."
systemctl daemon-reload
systemctl restart citadel-hub.service
sleep 2
echo "  ✅ Hub restarted."
echo ""

# ── Step 4: Verify single port listener ──
echo "[4/5] Verifying port 50051..."
LISTENERS=$(ss -tlnp 'sport = :50051' | grep -c LISTEN)
if [ "$LISTENERS" -eq 1 ]; then
    echo "  ✅ Exactly 1 listener on port 50051 — CORRECT"
elif [ "$LISTENERS" -gt 1 ]; then
    echo "  ❌ WARNING: $LISTENERS listeners detected — there may be a stale process"
    echo "     Run: ss -tlnp | grep 50051"
else
    echo "  ❌ WARNING: No listener on port 50051 — hub may have failed to start"
    echo "     Run: systemctl status citadel-hub.service"
fi
echo ""

# ── Step 5: Verify service is running ──
echo "[5/5] Service status:"
systemctl is-active citadel-hub.service && echo "  ✅ citadel-hub.service is ACTIVE" || echo "  ❌ citadel-hub.service is NOT active"
systemctl is-active obsidian-citadel.service 2>/dev/null && echo "  ❌ obsidian-citadel.service is still ACTIVE (should be gone)" || echo "  ✅ obsidian-citadel.service is properly disabled"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE"
echo ""
echo "  Test it:"
echo "    python3 /home/jack/system-mode-switcher/citadel_cli.py set Gaming"
echo "    sleep 12 && tail -10 /home/jack/system-mode-switcher/logs/citadel.log"
echo "═══════════════════════════════════════════════════════════════"
