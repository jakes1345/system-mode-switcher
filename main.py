#!/usr/bin/env python3
"""
🛡️ OBSIDIAN CITADEL — ENTERPRISE WORKSTATION CONTROL
Version: 3.0.0-APEX
"""

import sys
import os
from switcher.ui.app import SwitcherApp

if __name__ == "__main__":
    # Ensure project root is in path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    app = SwitcherApp()
    app.run(sys.argv)
