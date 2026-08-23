#!/usr/bin/env python3
"""Entry point for Obsidian Citadel."""

import os
import sys


def main():
    # Ensure we can import the package regardless of working directory
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    from switcher.ui.app import SwitcherApp
    app = SwitcherApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
