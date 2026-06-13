"""Desktop Notifications — cross-platform system notifications via plyer.

On Windows uses native Windows toast notifications (plyer -> winrt).
On other platforms falls through to plyer's platform implementation.
If plyer is unavailable, notifications degrade to log messages.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("rastro.desktop.notifications")

_HAS_PLYER = False
try:
    from plyer import notification as plyer_notification
    _HAS_PLYER = True
except ImportError:
    pass

_SILENT_MODE = False


def set_silent_mode(silent: bool = True) -> None:
    """Enable or disable silent mode. When silent, only logs are written."""
    global _SILENT_MODE
    _SILENT_MODE = silent
    if silent:
        logger.debug("Silent mode enabled — desktop notifications suppressed")


def _notify_plyer(title: str, message: str, urgency: str = "normal") -> bool:
    try:
        plyer_notification.notify(
            title=title,
            message=message,
            app_name="Rastro",
            timeout=5000,
            urgency=urgency,
        )
        return True
    except Exception as exc:
        logger.debug("plyer notification failed: %s", exc)
        return False


def send_notification(title: str, message: str, urgency: str = "normal") -> None:
    """Send a desktop notification. No-ops in silent mode."""
    if _SILENT_MODE:
        logger.debug("[Notification suppressed] %s: %s", title, message)
        return

    if _HAS_PLYER:
        if _notify_plyer(title, message, urgency):
            return

    logger.info("[NOTIFICATION] %s: %s", title, message)


# ── Convenience wrappers ────────────────────────────────────────────────


def notify_backend_started(port: int) -> None:
    send_notification("Rastro", "Backend server started", "normal")


def notify_dashboard_ready() -> None:
    send_notification("Rastro", "Dashboard ready — opening browser", "normal")


def notify_system_warning(message: str) -> None:
    send_notification("Rastro", message, "critical")


def notify_backend_restored() -> None:
    send_notification("Rastro", "Backend recovered after failure", "normal")


def notify_frontend_restored() -> None:
    send_notification("Rastro", "Frontend recovered after failure", "normal")
