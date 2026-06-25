"""Platform abstraction layer — OS detection, path resolution, config dirs.

Provides a single source of truth for platform-specific paths and behaviors.
All Rastro components should use this module instead of os.environ directly
for config/log/data directory resolution.

Usage:
    from core.platform.system import get_platform, Platform, get_data_dir
    plat = get_platform()
    data_dir = get_data_dir()
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Optional


class Platform:
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


def _raw_platform() -> str:
    raw = platform.system().lower()
    if raw.startswith("win"):
        return Platform.WINDOWS
    if raw.startswith("linux"):
        return Platform.LINUX
    if raw.startswith("darwin"):
        return Platform.MACOS
    return Platform.UNKNOWN


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def is_windows() -> bool:
    return _raw_platform() == Platform.WINDOWS


def is_linux() -> bool:
    return _raw_platform() == Platform.LINUX


def is_macos() -> bool:
    return _raw_platform() == Platform.MACOS


def get_platform() -> str:
    return _raw_platform()


class PlatformInfo:
    """Structured platform information."""

    def __init__(self) -> None:
        self.os: str = _raw_platform()
        self.frozen: bool = is_frozen()
        self.python: str = sys.version.split()[0]
        self.arch: str = platform.machine()
        self.hostname: str = platform.node()
        self.executable: str = sys.executable
        self.meipass: Optional[str] = getattr(sys, "_MEIPASS", None)

    @property
    def is_windows(self) -> bool:
        return self.os == Platform.WINDOWS

    @property
    def is_linux(self) -> bool:
        return self.os == Platform.LINUX

    @property
    def is_macos(self) -> bool:
        return self.os == Platform.MACOS

    def summary(self) -> str:
        mode = "frozen" if self.frozen else "dev"
        return f"{self.os}/{self.arch} {mode}"


# ─── Path resolution ──────────────────────────────────────────────────

def get_project_root() -> Path:
    """Return the project root directory.

    In frozen mode, returns sys._MEIPASS (PyInstaller temp dir).
    In dev mode, walks up from this file to find the project root.
    """
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_executable_dir() -> Path:
    """Return the directory containing the running executable.

    In frozen mode, returns the directory of the binary.
    In dev mode, returns the project root.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return get_project_root()


def get_data_dir() -> Path:
    """Return the persistent data directory for this platform.

    - Windows: %APPDATA%/Rastro
    - macOS:   ~/Library/Application Support/Rastro
    - Frozen:  next to the executable (Linux only, Windows prioritizes APPDATA)
    - Default: ~/.rastro
    """
    import logging
    _log = logging.getLogger("rastro.platform.system")
    _diag_path = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "Rastro", "license_diagnostic.log",
    )

    if is_windows():
        base = os.environ.get("APPDATA", "")
        result = Path(base) / "Rastro" if base else Path.home() / ".rastro"
        _log.info("PLATFORM_DIAG: is_windows=True APPDATA=%s data_dir=%s", base, result)
        _append_diag(_diag_path, f"[PATH-DIAG] Windows: APPDATA={base} → data_dir={result}")
        return result

    if is_macos():
        base = Path.home() / "Library" / "Application Support"
        result = base / "Rastro"
        _log.info("PLATFORM_DIAG: is_macos=True data_dir=%s", result)
        _append_diag(_diag_path, f"[PATH-DIAG] macOS: data_dir={result}")
        return result

    if is_frozen():
        result = get_executable_dir() / "data"
        _log.info("PLATFORM_DIAG: is_frozen=True executable_dir=%s data_dir=%s", get_executable_dir(), result)
        _append_diag(_diag_path, f"[PATH-DIAG] Frozen: executable_dir={get_executable_dir()} → data_dir={result}")
        return result

    result = Path.home() / ".rastro"
    _log.info("PLATFORM_DIAG: default data_dir=%s", result)
    _append_diag(_diag_path, f"[PATH-DIAG] Default (Linux dev): data_dir={result}")
    return result


def _append_diag(path: str, msg: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass


def get_config_dir() -> Path:
    """Return the config directory for this platform.

    - Windows: %APPDATA%/Rastro
    - macOS:   ~/Library/Application Support/Rastro
    - Default: ~/.rastro
    """
    if is_windows():
        base = os.environ.get("APPDATA", "")
        if base:
            return Path(base) / "Rastro"

    if is_macos():
        base = Path.home() / "Library" / "Application Support"
        return base / "Rastro"

    return Path.home() / ".rastro"


def get_log_dir() -> Path:
    """Return the log directory for this platform.

    Subdirectory of data_dir named 'logs'.
    """
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_db_path() -> Path:
    """Return the database file path (persistent across restarts)."""
    db_dir = get_data_dir() / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "rastro.db"


def get_frontend_dist_dir() -> Path:
    """Return the frontend dist directory.

    In frozen mode, looks for frontend_dist bundled with PyInstaller.
    In dev mode, uses the project frontend/dist/.
    """
    if is_frozen():
        candidate = get_project_root() / "frontend_dist"
        if candidate.is_dir():
            return candidate
    return get_project_root() / "frontend" / "dist"


# ─── Singleton ────────────────────────────────────────────────────────

_INFO: Optional[PlatformInfo] = None


def get_platform_info() -> PlatformInfo:
    global _INFO
    if _INFO is None:
        _INFO = PlatformInfo()
    return _INFO
