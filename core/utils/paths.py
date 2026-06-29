"""ORION Path Resolution — single source of truth for all file paths.

Resolves paths dynamically across all runtime environments:
  - Windows EXE (PyInstaller frozen)
  - Windows portable (ZIP)
  - WSL dev (/home/...)
  - Native Linux dev

Usage:
    from core.utils.paths import get_app_root, get_data_path

Rules:
  - NEVER hardcode WSL or Windows paths
  - ALL paths are dynamic based on runtime environment
  - Frozen EXE: data lives next to executable (portable)
  - Installed (Windows): data lives in %APPDATA%/ORION
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("orion.paths")

# ── Environment detection (simple, no cross-imports) ───────────────────


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _is_wsl() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    try:
        with open("/proc/version") as f:
            content = f.read().lower()
            return "microsoft" in content or "wsl" in content
    except OSError:
        return False


def _is_portable() -> bool:
    """Detect portable mode — exe in a user-writable location (not Program Files)."""
    if not _is_frozen():
        return False
    exe_dir = Path(sys.executable).resolve().parent
    program_files = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
    return not str(exe_dir).lower().startswith(str(program_files).lower())


# ── Path resolution ────────────────────────────────────────────────────


def _discover_root() -> Path:
    """Discover the application root directory dynamically."""
    if _is_frozen():
        return Path(sys._MEIPASS)
    # Dev mode: this file is at core/utils/paths.py, root is ../../ (3 levels up)
    return Path(__file__).resolve().parent.parent.parent


def _discover_exe_dir() -> Path:
    """Discover the directory containing the executable or script."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


_APP_ROOT: Path | None = None
_EXE_DIR: Path | None = None


def _get_app_root() -> Path:
    global _APP_ROOT
    if _APP_ROOT is None:
        _APP_ROOT = _discover_root()
    return _APP_ROOT


def _get_exe_dir() -> Path:
    global _EXE_DIR
    if _EXE_DIR is None:
        _EXE_DIR = _discover_exe_dir()
    return _EXE_DIR


# ── Public API ─────────────────────────────────────────────────────────


def get_app_root() -> Path:
    """Return the application root directory.

    Frozen:  sys._MEIPASS (PyInstaller temp extraction)
    Dev:     project root (parent of core/, api/, desktop/)
    """
    return _get_app_root()


def get_exe_dir() -> Path:
    """Return the directory containing the executable.

    Frozen:  directory of Orion.exe
    Dev:     project root
    """
    return _get_exe_dir()


def get_data_path() -> Path:
    """Return the persistent data directory.

    Order of precedence:
      1. ORION_DATA_DIR env var (explicit override)
      2. Portable/frozen: next to executable
      3. Windows installed: %APPDATA%/ORION
      4. WSL/Linux dev: ~/.orion
    """
    env_dir = os.environ.get("ORION_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    if _is_frozen() and _is_portable():
        return _get_exe_dir() / "data"

    if _is_windows():
        base = os.environ.get("APPDATA", "")
        if base:
            return Path(base) / "ORION"

    if _is_wsl():
        return Path.home() / ".orion"

    return Path.home() / ".orion"


def get_config_path() -> Path:
    """Return the config directory."""
    return get_data_path() / "config"


def get_db_path() -> Path:
    """Return the database file path."""
    db_dir = get_data_path() / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "orion.db"


def get_log_path() -> Path:
    """Return the log directory."""
    log_dir = get_data_path() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_frontend_path() -> Path | None:
    """Return the frontend dist directory, or None if not found."""
    if _is_frozen():
        candidates = [
            _get_app_root() / "frontend_dist",
            _get_exe_dir() / "frontend_dist",
        ]
    else:
        candidates = [
            _get_app_root() / "frontend" / "dist",
            _get_app_root() / "frontend_dist",
        ]

    for c in candidates:
        if c.is_dir() and (c / "index.html").is_file():
            return c
    return None


def get_settings_path() -> Path:
    """Return the settings JSON file path."""
    config_dir = get_config_path()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"


def get_icon_path() -> Path | None:
    """Return the application icon path."""
    if _is_frozen():
        candidates = [
            _get_exe_dir() / "orion.ico",
            _get_app_root() / "orion.ico",
        ]
    else:
        candidates = [
            _get_app_root() / "installer" / "icons" / "orion.ico",
        ]
    for c in candidates:
        if c.exists():
            return c
    return None
