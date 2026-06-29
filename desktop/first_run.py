"""ORION First Run Experience — runs exactly once on first launch.

Executes:
  - Register OS-level autostart (Windows primary)
  - Initialize config directory
  - Create device identity
  - Mark first_run_complete = True

After completion, this module is never invoked again.
"""

from __future__ import annotations

import logging
import platform
from pathlib import Path

from desktop.autostart import enable_autostart, is_autostart_enabled
from desktop.settings import DesktopSettings

logger = logging.getLogger("orion.desktop.first_run")


def run_first_time(settings: DesktopSettings) -> bool:
    """Execute all first-run setup steps.

    Returns True if first run was completed, False if already done.
    """
    if settings.get("first_run_complete", False):
        return False

    logger.info("First run detected — running initial setup")

    _detect_and_register_autostart(settings)
    _init_config(settings)
    _create_identity(settings)

    settings.set("first_run_complete", True)
    settings.set("first_run", False)

    logger.info("First run setup complete")
    return True


def _detect_and_register_autostart(settings: DesktopSettings) -> None:
    """Detect OS and register autostart if supported."""
    system = platform.system()
    logger.info("Detected OS: %s — registering autostart", system)

    try:
        if not is_autostart_enabled():
            result = enable_autostart()
            if result:
                settings.set("auto_start", True)
                logger.info("Autostart registered successfully")
            else:
                logger.warning("Autostart registration not available on this system")
        else:
            logger.info("Autostart already enabled")
    except Exception as exc:
        logger.warning("Failed to register autostart: %s", exc)


def _init_config(settings: DesktopSettings) -> None:
    """Ensure config directory and log directory exist."""
    config_dir = Path(settings.config_path)
    config_dir.mkdir(parents=True, exist_ok=True)

    log_dir = config_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Config directory: %s", config_dir)
    logger.info("Log directory: %s", log_dir)


def _create_identity(settings: DesktopSettings) -> None:
    """Ensure device identity exists."""
    device_id = settings.ensure_device_id()
    logger.info("Device identity: %s", device_id)


def is_first_run_complete(settings: DesktopSettings) -> bool:
    """Check if first-run setup has been completed."""
    return settings.get("first_run_complete", False)
