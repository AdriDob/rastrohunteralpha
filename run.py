#!/usr/bin/env python3
"""Rastro — one-command launcher.

Usage:
    python run.py                        # Desktop mode (auto-detect)
    python run.py --service              # Run as Windows Service (SCM)
    python run.py --tray                 # System tray only (service assumed running)
    python run.py --browser              # Browser mode
    python run.py --install-service      # Register Windows Service
    python run.py --remove-service       # Unregister Windows Service
    python run.py --install              # Run installer and exit
    python run.py --start                # Force desktop mode
    python run.py --check                # Self-diagnostic quick check
    python run.py --dev                  # Dev mode (verbose logging)

Architecture:
  - Single entrypoint for dev, frozen (PyInstaller), and CI
  - Injects PROJECT_ROOT into sys.path for reliable imports
  - Supports multiple modes: desktop, service, tray, CLI
  - Auto-builds frontend in dev mode when dist/ is missing
"""

import sys
from pathlib import Path

BASE_DIR = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _ensure_frontend_build() -> None:
    if getattr(sys, "frozen", False):
        return
    dist = BASE_DIR / "frontend" / "dist"
    if not dist.is_dir() or not list(dist.rglob("*.html")):
        import subprocess
        print("[run] Building frontend...")
        subprocess.run(["npm", "install", "--silent"], cwd=BASE_DIR / "frontend", check=True)
        subprocess.run(["npm", "run", "build"], cwd=BASE_DIR / "frontend", check=True)
        print("[run] Frontend built.")


def _run_diagnostics() -> None:
    print("[run] Running self-diagnostics...")
    results: list[tuple[str, bool, str]] = []

    # Check Python version
    py_ok = sys.version_info >= (3, 10)
    results.append(("Python", py_ok, f"{sys.version_info.major}.{sys.version_info.minor}"))
    if not py_ok:
        print("[run]  ERROR: Python 3.10+ required")
        sys.exit(1)

    # Check project root
    root_ok = (BASE_DIR / "api" / "main.py").exists()
    results.append(("Project root", root_ok, str(BASE_DIR)))

    # Check frontend dist
    frontend = BASE_DIR / "frontend" / "dist"
    if frontend.is_dir() and list(frontend.rglob("*.html")):
        size_kb = sum(f.stat().st_size for f in frontend.rglob("*") if f.is_file()) / 1024
        results.append(("Frontend", True, f"{size_kb:.0f} KB"))
    else:
        results.append(("Frontend", False, "not built — run --install first"))

    # Check database
    db_path = BASE_DIR / "database" / "rastro.db"
    if db_path.exists():
        size_mb = db_path.stat().st_size / 1024 / 1024
        results.append(("Database", True, f"{size_mb:.1f} MB"))
    else:
        results.append(("Database", False, "not found — will be created on first run"))

    # Check PyInstaller build
    if getattr(sys, "frozen", False):
        results.append(("Build", True, "frozen (PyInstaller)"))
    else:
        exe = BASE_DIR / "dist" / "Rastro" / ("Rastro.exe" if sys.platform == "win32" else "Rastro")
        if exe.exists():
            results.append(("Build", True, f"{exe.stat().st_size / 1024 / 1024:.1f} MB"))
        else:
            results.append(("Build", False, "not built — run with --install first"))

    # Check installed output
    output = BASE_DIR / "build_info.json"
    if output.exists():
        results.append(("Install info", True, str(output)))
    else:
        one_drive_home = Path.home() / "OneDrive" / "Desktop" / "Yo" / "privado" / "Rastro"
        installed = one_drive_home / "build_info.json"
        if installed.exists():
            results.append(("Install info", True, str(installed)))
        else:
            results.append(("Install info", False, "not found (not installed)"))

    # Print results
    print()
    print(f"  {'Check':<20} {'Status':<8} Detail")
    print(f"  {'─'*20} {'─'*8} {'─'*30}")
    for name, ok, detail in results:
        status = "OK" if ok else "FAIL"
        print(f"  {name:<20} [{status:>4}] {detail}")

    all_ok = all(r[1] for r in results)
    print()
    if all_ok:
        print("[run] All diagnostics passed")
    else:
        print("[run] Some checks failed — run `python run.py --install` to set up")
        sys.exit(1)


def main() -> None:
    args = set(sys.argv[1:])

    if "--install" in args:
        import subprocess
        install_args = [a for a in sys.argv[1:] if a != "--install"]
        subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "install.py"), *install_args])
        return

    if "--check" in args:
        _run_diagnostics()
        return

    if "--start" in args:
        _ensure_frontend_build()
        from desktop.main_desktop import main as desktop_main
        desktop_main()
        return

    if "--install-service" in args:
        _ensure_frontend_build()
        try:
            from desktop.service import install_service
            install_service()
        except ImportError:
            print("[run] Service module not available (Windows only)")
            sys.exit(1)
        return

    if "--remove-service" in args:
        try:
            from desktop.service import remove_service
            remove_service()
        except ImportError:
            print("[run] Service module not available (Windows only)")
            sys.exit(1)
        return

    if "--service" in args:
        _ensure_frontend_build()
        from desktop.service import run_service
        run_service()
        return

    if "--tray" in args:
        from desktop.tray import run_tray_only
        run_tray_only(
            port=8000,
            host="127.0.0.1",
        )
        return

    _ensure_frontend_build()

    if "--browser" in args:
        from desktop.main_desktop import main as desktop_main
        desktop_main()
        return

    try:
        from desktop.service_util import is_service_running
        if is_service_running():
            print("[run] Service is running — launching tray mode")
            from desktop.tray import run_tray_only
            run_tray_only(port=8000, host="127.0.0.1")
            return
    except ImportError:
        pass

    from desktop.main_desktop import main as desktop_main
    desktop_main()


if __name__ == "__main__":
    main()
