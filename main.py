#!/usr/bin/env python3
"""
🛡️ OBSIDIAN CITADEL — ENTERPRISE WORKSTATION CONTROL
Version: 3.0.0-APEX
"""

import sys
import os

pkg_dir = os.path.dirname(os.path.abspath(__file__))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from switcher.ui.app import SwitcherApp

if __name__ == "__main__":
    app = SwitcherApp()
    app.run(sys.argv)
