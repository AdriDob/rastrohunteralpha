"""Auto-Start with OS — OS-level autostart integration.

Target platforms:
  - Windows (primary): Startup script in %APPDATA%\\...\\Startup\\
  - macOS (optional): LaunchAgent plist in ~/Library/LaunchAgents/

Linux support removed per product strategy (see Phase 1 migration).
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys

logger = logging.getLogger("rastro.desktop.autostart")

LAUNCHER_CMD = f"{sys.executable} -m desktop.main_desktop --no-tray"

LAUNCHD_PLIST = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rastro.desktop</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>desktop.main_desktop</string>
        <string>--silent</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>RASTRO_DESKTOP</key>
        <string>1</string>
    </dict>
</dict>
</plist>
"""

STARTUP_SCRIPT = f"""@echo off
start "" "{sys.executable}" -m desktop.main_desktop --no-tray
"""


def _windows_startup_path() -> str | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return os.path.join(
        appdata,
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
        "Rastro.bat",
    )


def _launchd_path() -> str | None:
    home = os.environ.get("HOME")
    if not home:
        return None
    return os.path.join(home, "Library", "LaunchAgents", "com.rastro.desktop.plist")


def _get_autostart_path() -> str | None:
    system = platform.system()
    if system == "Darwin":
        return _launchd_path()
    return _windows_startup_path()


# ── Enable ───────────────────────────────────────────────────────────

def _enable_windows() -> bool:
    path = _windows_startup_path()
    if not path:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w") as f:
            f.write(STARTUP_SCRIPT)
        logger.info("Windows startup script installed: %s", path)
        return True
    except Exception as exc:
        logger.warning("Failed to install Windows startup: %s", exc)
        return False


def _enable_macos() -> bool:
    path = _launchd_path()
    if not path:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w") as f:
            f.write(LAUNCHD_PLIST)
        subprocess.run(["launchctl", "load", path], capture_output=True, timeout=10)
        logger.info("LaunchAgent installed: %s", path)
        return True
    except Exception as exc:
        logger.warning("Failed to install LaunchAgent: %s", exc)
        return False


def enable_autostart() -> bool:
    """Install OS-level autostart for the current platform.

    Returns True if successful, False otherwise.
    """
    system = platform.system()
    logger.info("Enabling autostart for %s", system)

    if system == "Windows":
        return _enable_windows()
    elif system == "Darwin":
        return _enable_macos()

    logger.warning("Unsupported OS for autostart: %s", system)
    return False


# ── Disable ──────────────────────────────────────────────────────────

def _disable_windows() -> bool:
    path = _windows_startup_path()
    if path and os.path.exists(path):
        try:
            os.remove(path)
            logger.info("Windows startup script removed: %s", path)
            return True
        except Exception as exc:
            logger.warning("Failed to remove Windows startup: %s", exc)
            return False
    return True


def _disable_macos() -> bool:
    path = _launchd_path()
    if path and os.path.exists(path):
        try:
            subprocess.run(["launchctl", "unload", path], capture_output=True, timeout=10)
            os.remove(path)
            logger.info("LaunchAgent removed: %s", path)
            return True
        except Exception as exc:
            logger.warning("Failed to remove LaunchAgent: %s", exc)
            return False
    return True


def disable_autostart() -> bool:
    """Remove OS-level autostart for the current platform.

    Returns True if successful (or nothing to remove), False on error.
    """
    system = platform.system()
    logger.info("Disabling autostart for %s", system)

    if system == "Windows":
        return _disable_windows()
    elif system == "Darwin":
        return _disable_macos()

    logger.warning("Unsupported OS for autostart: %s", system)
    return False


# ── Check ────────────────────────────────────────────────────────────

def is_autostart_enabled() -> bool:
    """Check if Rastro is configured to start with the OS.

    Returns True if autostart is configured, False otherwise.
    """
    path = _get_autostart_path()
    return bool(path and os.path.exists(path))


# ── Legacy compatibility ────────────────────────────────────────────

def install_autostart() -> bool:
    return enable_autostart()


def remove_autostart() -> bool:
    return disable_autostart()
