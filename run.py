#!/usr/bin/env python3
"""Rastro — one-command launcher.

Usage:
    python run.py              # Desktop window (pywebview)
    python run.py --browser    # Browser mode
    python run.py --dev        # Dev mode (verbose logging)

Architecture:
  - Single entrypoint for dev, frozen (PyInstaller), and CI
  - Injects PROJECT_ROOT into sys.path for reliable imports
  - Auto-builds frontend in dev mode when dist/ is missing
"""

import os
import sys
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────────────
# Must run before ANY project import to ensure module resolution works
# in both dev (`python run.py`) and frozen (`dist/Rastro/Rastro`) modes.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _ensure_frontend_build() -> None:
    """Auto-build frontend when dist/ is missing (dev mode only)."""
    if getattr(sys, "frozen", False):
        return  # frontend_dist bundled inside the binary

    dist = BASE_DIR / "frontend" / "dist"
    if not dist.is_dir() or not list(dist.rglob("*.html")):
        import subprocess
        print("[run] Building frontend...")
        subprocess.run(
            ["npm", "install", "--silent"],
            cwd=BASE_DIR / "frontend", check=True,
        )
        subprocess.run(
            ["npm", "run", "build"],
            cwd=BASE_DIR / "frontend", check=True,
        )
        print("[run] Frontend built.")


def _startup_diag():
    import time as _time
    _marker = f"[STARTUP] Rastro DIAG build @ {_time.ctime()}"
    _frozen = getattr(sys, "frozen", False)
    _os_name = os.name
    _appdata = os.environ.get("APPDATA", "NOT SET")
    _userprof = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    _desktop = os.path.join(_userprof, "Desktop")
    _lines = [
        _marker,
        f"[STARTUP] sys.frozen={_frozen}",
        f"[STARTUP] os.name={_os_name}",
        f"[STARTUP] APPDATA={_appdata}",
        f"[STARTUP] USERPROFILE={_userprof}",
        f"[STARTUP] sys.argv={sys.argv}",
        f"[STARTUP] cwd={os.getcwd()}",
    ]

    _logpath = os.path.join(_appdata, "Rastro", "license_diagnostic.log")
    _altpath = os.path.join(_desktop, "rastro_diag.log")
    _written = False
    for _p in (_logpath, _altpath):
        try:
            os.makedirs(os.path.dirname(_p), exist_ok=True)
            with open(_p, "a", encoding="utf-8") as _f:
                for _l in _lines:
                    _f.write(_l + "\n")
            _written = True
        except Exception as _e:
            _lines.append(f"[STARTUP] FAILED to write to {_p}: {_e}")

    if not _written:
        _emergency = os.path.join(_desktop, "rastro_emergency.txt")
        try:
            with open(_emergency, "w") as _f:
                for _l in _lines:
                    _f.write(_l + "\n")
        except Exception:
            pass

    if _frozen and _os_name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                _marker + "\n\nAPPDATA=" + _appdata +
                "\nUSERPROFILE=" + _userprof +
                "\n\nLogs written to:\n  " + _logpath + "\n  " + _altpath,
                "Rastro DIAG", 0,
            )
        except Exception:
            pass


def main() -> None:
    _startup_diag()
    _ensure_frontend_build()
    from desktop.main_desktop import main as desktop_main
    desktop_main()


if __name__ == "__main__":
    main()
