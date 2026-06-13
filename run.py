#!/usr/bin/env python3
"""Rastro — one-command launcher.

Usage:
    python run.py              # Desktop window (pywebview)
    python run.py --browser    # Browser mode
    python run.py --dev        # Dev mode (verbose logging)
"""

import os
import sys
from pathlib import Path


def _ensure_frontend_build() -> None:
    dist = Path(__file__).resolve().parent / "frontend" / "dist"
    if not dist.is_dir() or not list(dist.rglob("*.html")):
        print("[run] Building frontend...")
        import subprocess
        subprocess.run(
            ["npm", "install", "--silent"],
            cwd=Path(__file__).resolve().parent / "frontend",
            check=True,
        )
        subprocess.run(
            ["npm", "run", "build"],
            cwd=Path(__file__).resolve().parent / "frontend",
            check=True,
        )
        print("[run] Frontend built.")


def main() -> None:
    # Ensure we're in the project root
    os.chdir(Path(__file__).resolve().parent)

    _ensure_frontend_build()

    from desktop.main_desktop import main as desktop_main
    desktop_main()


if __name__ == "__main__":
    main()
