"""Lightweight service detection — always safe to import.

Provides `is_service_installed()` and `is_service_running()` without
ever importing pywin32 at module level.  Each function uses a lazy
import inside its own body, so this file has zero side effects.

Importing this module will never crash, even if pywin32 is missing or
only partially installed.
"""

from __future__ import annotations

SERVICE_NAME = "Orion"


def _win32_modules() -> tuple[bool, object, object]:
    """Return (available, win32service, win32serviceutil)."""
    try:
        import win32service as _sv
        import win32serviceutil as _su
        return True, _sv, _su
    except ImportError:
        return False, None, None


def is_service_installed() -> bool:
    available, _, serviceutil = _win32_modules()
    if not available:
        return False
    try:
        status = serviceutil.QueryServiceStatus(SERVICE_NAME)
        return status is not None
    except Exception:
        return False


def is_service_running() -> bool:
    available, service, serviceutil = _win32_modules()
    if not available:
        return False
    try:
        status = serviceutil.QueryServiceStatus(SERVICE_NAME)
        return status[1] == service.SERVICE_RUNNING
    except Exception:
        return False
