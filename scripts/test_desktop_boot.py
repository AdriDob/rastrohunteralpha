#!/usr/bin/env python3
"""Desktop Boot Validation — tests the single-process architecture.

Tests:
  1. Path resolution (frozen & dev)
  2. main_desktop import and helpers
  3. Frontend dist detection
  4. serve_frontend module
  5. Settings and first-run

Usage:
    python scripts/test_desktop_boot.py
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TEST] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("test_desktop_boot")

PASS = 0
FAIL = 0
SKIP = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        log.info("  PASS  %s", name)
    else:
        FAIL += 1
        log.error("  FAIL  %s%s", name, f" — {detail}" if detail else "")


def check_skip(name: str) -> None:
    global SKIP
    SKIP += 1
    log.info("  SKIP  %s", name)


def section(title: str) -> None:
    log.info("")
    log.info("=" * 60)
    log.info("  %s", title)
    log.info("=" * 60)


# ── 1. Path resolution ──────────────────────────────────────────────────


def test_path_resolution() -> None:
    section("1. Path Resolution")

    from core_engines.platform.system import (
        get_config_dir,
        get_data_dir,
        get_frontend_dist_dir,
        get_project_root,
        is_frozen,
    )

    check("is_frozen() returns bool", isinstance(is_frozen(), bool))

    root = get_project_root()
    check("get_project_root() returns Path", isinstance(root, Path))
    check("get_project_root() exists", root.exists())

    frontend_dist = get_frontend_dist_dir()
    check("get_frontend_dist_dir() returns Path", isinstance(frontend_dist, Path))

    if frontend_dist.exists():
        check("Frontend dist directory exists", True)
        index = frontend_dist / "index.html"
        check("Frontend index.html exists", index.is_file())
    else:
        check("Frontend dist directory exists (build required)", False,
              "run: cd frontend && npm run build")

    data_dir = get_data_dir()
    check("get_data_dir() returns Path", isinstance(data_dir, Path))
    check("get_data_dir() does not contain XDG (no Linux fallback)",
          "xdg" not in str(data_dir).lower() and ".local/share" not in str(data_dir))

    config_dir = get_config_dir()
    check("get_config_dir() returns Path", isinstance(config_dir, Path))
    check("get_config_dir() does not contain XDG (no Linux fallback)",
          "xdg" not in str(config_dir).lower() and ".config/rastro" not in str(config_dir))

    # Simulate frozen path
    orig_frozen = getattr(sys, "frozen", False)
    try:
        sys.frozen = True
        sys._MEIPASS = str(root)
        frozen_root = get_project_root()
        check("Frozen get_project_root() == sys._MEIPASS", str(frozen_root) == str(root))
    finally:
        if orig_frozen:
            sys.frozen = True
        else:
            if hasattr(sys, "frozen"):
                delattr(sys, "frozen")
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")

    log.info("")


# ── 2. main_desktop module ──────────────────────────────────────────────


def test_main_desktop_entry() -> None:
    section("2. main_desktop Entry Point")

    import importlib
    mod = importlib.import_module("desktop.main_desktop")

    check("main() exists", hasattr(mod, "main"))
    check("ServerThread class exists", hasattr(mod, "ServerThread"))
    check("_setup_logging exists", hasattr(mod, "_setup_logging"))
    check("_wait_for_port exists", hasattr(mod, "_wait_for_port"))
    check("_wait_for_health exists", hasattr(mod, "_wait_for_health"))
    check("_mount_frontend exists", hasattr(mod, "_mount_frontend"))

    # Verify no subprocess/multiprocessing dependencies
    import inspect
    source = inspect.getsource(mod)
    check("No subprocess.Popen usage", "Popen" not in source)
    check("No multiprocessing module import", "import multiprocessing" not in source)
    check("No subprocess usage", "subprocess" not in source)

    # Test ServerThread can be instantiated
    thread = mod.ServerThread("127.0.0.1", 18000)
    check("ServerThread created", thread is not None)
    check("ServerThread has stop()", hasattr(thread, "stop"))
    check("ServerThread has start()", hasattr(thread, "start"))

    log.info("")


# ── 3. Frontend detection ──────────────────────────────────────────────


def test_frontend_detection() -> None:
    section("3. Frontend Detection")

    from core_engines.platform.system import get_frontend_dist_dir
    dist_dir = get_frontend_dist_dir()
    check("Frontend dist dir ends with frontend/dist or frontend_dist",
          str(dist_dir).endswith(("frontend/dist", "frontend_dist")))

    from desktop.serve_frontend import mount_frontend
    check("mount_frontend() exists", callable(mount_frontend))

    log.info("")


# ── 4. serve_frontend module ──────────────────────────────────────────


def test_serve_frontend() -> None:
    section("4. serve_frontend Module")

    import importlib
    mod = importlib.import_module("desktop.serve_frontend")
    check("create_app() exists", hasattr(mod, "create_app"))
    check("mount_frontend() exists", hasattr(mod, "mount_frontend"))

    app = mod.create_app("/nonexistent")
    check("create_app() returns app", app is not None)
    check("App has FastAPI title", app.title == "Rastro Frontend")

    log.info("")


# ── 5. Settings and autostart ─────────────────────────────────────────


def test_settings_and_autostart() -> None:
    section("5. Settings and autostart")

    from desktop.settings import DEFAULT_SETTINGS
    check("DesktopSettings importable", True)
    check("DEFAULT_SETTINGS has first_run", "first_run" in DEFAULT_SETTINGS)
    check("DEFAULT_SETTINGS has onboarding_complete", "onboarding_complete" in DEFAULT_SETTINGS)

    from desktop.autostart import disable_autostart, enable_autostart, is_autostart_enabled
    check("enable_autostart exists", callable(enable_autostart))
    check("disable_autostart exists", callable(disable_autostart))
    check("is_autostart_enabled exists", callable(is_autostart_enabled))

    import platform
    if platform.system() == "Windows" or platform.system() == "Darwin":
        check("is_autostart_enabled returns bool on supported OS",
              isinstance(is_autostart_enabled(), bool))
    else:
        check_skip("is_autostart_enabled (not Windows/macOS)")

    from desktop.first_run import is_first_run_complete, run_first_time
    check("run_first_time exists", callable(run_first_time))
    check("is_first_run_complete exists", callable(is_first_run_complete))

    log.info("")


# ── 6. Platform abstraction ──────────────────────────────────────────


def test_platform_abstraction() -> None:
    section("6. Platform Abstraction")

    from core_engines.platform.system import (
        get_platform,
        get_platform_info,
        is_frozen,
        is_linux,
        is_macos,
        is_windows,
    )

    check("get_platform() returns str", isinstance(get_platform(), str))
    check("is_windows() returns bool", isinstance(is_windows(), bool))
    check("is_linux() returns bool", isinstance(is_linux(), bool))
    check("is_macos() returns bool", isinstance(is_macos(), bool))
    check("is_frozen() returns bool", isinstance(is_frozen(), bool))

    info = get_platform_info()
    check("PlatformInfo has os", hasattr(info, "os"))
    check("PlatformInfo has frozen", hasattr(info, "frozen"))
    check("PlatformInfo has python", hasattr(info, "python"))
    check("PlatformInfo.summary() returns str", isinstance(info.summary(), str))

    log.info("")


# ── 7. Notifications (plyer-only) ─────────────────────────────────────


def test_notifications() -> None:
    section("7. Notifications (plyer-only)")

    import importlib
    mod = importlib.import_module("desktop.notifications")
    check("send_notification exists", hasattr(mod, "send_notification"))
    check("set_silent_mode exists", hasattr(mod, "set_silent_mode"))

    import inspect
    source = inspect.getsource(mod)
    check("No notify-send fallback", "notify-send" not in source)

    log.info("")


# ── Main ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Test desktop boot sequence")
    parser.add_argument("--frozen", action="store_true", help="Simulate frozen mode path checks")
    parser.parse_args()

    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║     Rastro Desktop — Boot Validation Test          ║")
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("")
    log.info("  Python:   %s", sys.version.split()[0])
    log.info("  Platform: %s", sys.platform)
    log.info("  Frozen:   %s", getattr(sys, "frozen", False))
    log.info("  CWD:      %s", os.getcwd())
    log.info("")

    test_path_resolution()
    test_main_desktop_entry()
    test_frontend_detection()
    test_serve_frontend()
    test_settings_and_autostart()
    test_platform_abstraction()
    test_notifications()

    log.info("")
    log.info("=" * 60)
    log.info("  RESULTS:  %d PASS,  %d FAIL,  %d SKIP", PASS, FAIL, SKIP)
    log.info("=" * 60)
    log.info("")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
