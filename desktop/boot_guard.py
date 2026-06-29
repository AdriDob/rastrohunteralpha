"""BOOT GUARD — safe startup, environment detection, crash prevention.

Ensures ORION never crashes during boot. Every failure has a fallback.

Exports:
    RuntimeMode enum: WSL_DEV, WINDOWS_EXE, WINDOWS_PORTABLE, DEV
    validate_environment() -> dict of check results
    safe_import(module) -> module | None
    get_runtime_mode() -> RuntimeMode
    is_safe_mode() -> bool
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from enum import Enum
from pathlib import Path

logger = logging.getLogger("orion.boot_guard")

_SAFE_MODE = False
_RUNTIME_MODE: RuntimeMode | None = None


class RuntimeMode(Enum):
    WSL_DEV = "wsl_dev"
    WINDOWS_EXE = "windows_exe"
    WINDOWS_PORTABLE = "windows_portable"
    DEV = "dev"
    UNKNOWN = "unknown"


# ── Safe import ────────────────────────────────────────────────────────


def safe_import(module_name: str, package: str | None = None) -> object | None:
    """Import a module gracefully. Returns None instead of crashing."""
    try:
        return importlib.import_module(module_name, package=package)
    except ImportError:
        logger.debug("safe_import: %s not available", module_name)
        return None
    except Exception as exc:
        logger.warning("safe_import: %s raised %s: %s", module_name, type(exc).__name__, exc)
        return None


# ── Environment detection ──────────────────────────────────────────────


def _is_wsl() -> bool:
    """Detect WSL (Windows Subsystem for Linux) environment."""
    if not sys.platform.startswith("linux"):
        return False
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except OSError:
        return False


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _get_executable_dir() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _has_frontend_dist() -> bool:
    """Check if frontend dist exists in any expected location."""
    if _is_frozen():
        candidates = [
            Path(sys._MEIPASS) / "frontend_dist",
            Path(sys.executable).parent / "frontend_dist",
        ]
    else:
        candidates = [
            Path(__file__).resolve().parent.parent / "frontend" / "dist",
            Path(__file__).resolve().parent.parent / "frontend_dist",
        ]
    for c in candidates:
        if c.is_dir() and (c / "index.html").is_file():
            return True
    return False


def _has_pywin32() -> bool:
    return safe_import("win32serviceutil") is not None


def _has_pystray() -> bool:
    return safe_import("pystray") is not None


def _has_webview() -> bool:
    return safe_import("webview") is not None


def get_runtime_mode() -> RuntimeMode:
    """Detect the runtime environment."""
    global _RUNTIME_MODE
    if _RUNTIME_MODE is not None:
        return _RUNTIME_MODE

    if _is_frozen():
        if _is_windows():
            _RUNTIME_MODE = RuntimeMode.WINDOWS_EXE
        else:
            _RUNTIME_MODE = RuntimeMode.WINDOWS_PORTABLE
    elif _is_wsl():
        _RUNTIME_MODE = RuntimeMode.WSL_DEV
    else:
        _RUNTIME_MODE = RuntimeMode.DEV

    logger.info("Runtime mode detected: %s", _RUNTIME_MODE.value)
    return _RUNTIME_MODE


def is_safe_mode() -> bool:
    """Check if the system is running in safe mode."""
    return _SAFE_MODE


def enable_safe_mode(reason: str = "") -> None:
    """Enable safe mode — degrades functionality but guarantees uptime."""
    global _SAFE_MODE
    _SAFE_MODE = True
    logger.warning("SAFE MODE enabled%s", f": {reason}" if reason else "")
    os.environ["ORION_SAFE_MODE"] = "1"


# ── Validation ─────────────────────────────────────────────────────────


def validate_environment() -> dict[str, dict]:
    """Run all environment checks, returning detailed results.

    Returns dict of check_name -> {"ok": bool, "detail": str, "fatal": bool}
    Using this, the launcher decides whether to activate safe mode.
    """
    mode = get_runtime_mode()
    results: dict[str, dict] = {}

    # Python version
    py_ok = sys.version_info >= (3, 10)
    results["python"] = {
        "ok": py_ok,
        "detail": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "fatal": not py_ok,
    }

    # Platform
    results["platform"] = {
        "ok": True,
        "detail": f"{sys.platform} / {mode.value}",
        "fatal": False,
    }

    # Frontend
    frontend_ok = _has_frontend_dist()
    results["frontend"] = {
        "ok": frontend_ok,
        "detail": "found" if frontend_ok else "not found (browser fallback available)",
        "fatal": False,
    }

    # PyWin32 (only relevant on Windows)
    if _is_windows():
        has_py = _has_pywin32()
        results["pywin32"] = {
            "ok": has_py,
            "detail": "available" if has_py else "not available (service mode disabled)",
            "fatal": False,  # Never fatal — degrades to UI mode
        }

    # pystray (system tray)
    has_tray = _has_pystray()
    results["pystray"] = {
        "ok": has_tray,
        "detail": "available" if has_tray else "not available (no system tray icon)",
        "fatal": False,
    }

    # webview (desktop window)
    has_wv = _has_webview()
    results["webview"] = {
        "ok": has_wv,
        "detail": "available" if has_wv else "not available (will use browser)",
        "fatal": False,
    }

    # Executable access (frozen only)
    if _is_frozen():
        exe = Path(sys.executable)
        exe_ok = exe.exists()
        results["executable"] = {
            "ok": exe_ok,
            "detail": str(exe) if exe_ok else "MISSING",
            "fatal": not exe_ok,
        }

    # API import test (lightweight)
    api_mod = safe_import("api.main")
    results["api"] = {
        "ok": api_mod is not None,
        "detail": "importable" if api_mod else "not found (will try anyway)",
        "fatal": False,
    }

    # Log summary
    results["_summary"] = {
        "mode": mode.value,
        "safe_mode": _SAFE_MODE,
        "all_critical_ok": all(
            v["ok"] or not v.get("fatal", False)
            for k, v in results.items()
            if not k.startswith("_")
        ),
    }

    return results


# ── Boot decision ──────────────────────────────────────────────────────


def should_activate_safe_mode(validation: dict[str, dict]) -> bool:
    """Determine if safe mode should be activated based on validation results."""
    if validation.get("_summary", {}).get("safe_mode", False):
        return True
    for name, check in validation.items():
        if name.startswith("_"):
            continue
        if not check["ok"] and check.get("fatal", False):
            logger.warning("Fatal check failed: %s — %s", name, check["detail"])
            return True
    return False


def boot_summary(validation: dict[str, dict]) -> str:
    """Generate a human-readable boot summary."""
    lines = ["ORION Boot Summary:"]
    for name, check in validation.items():
        if name.startswith("_"):
            continue
        icon = "OK" if check["ok"] else ("!!" if check.get("fatal") else "--")
        lines.append(f"  [{icon}] {name:<12} {check['detail']}")
    summary = validation.get("_summary", {})
    mode = summary.get("mode", "unknown")
    safe = "SAFE MODE" if summary.get("safe_mode") else "NORMAL"
    lines.append(f"  Mode: {mode} / {safe}")
    return "\n".join(lines)
