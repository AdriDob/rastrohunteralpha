"""Firebase Cloud Messaging adapter — HTTP v1 API."""

from __future__ import annotations

import contextlib
import logging
import os
from typing import Any

import httpx

from database import db

logger = logging.getLogger("rastro.notifications.fcm")

FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"


class FCMAdapter:
    def __init__(self) -> None:
        self._server_key = os.environ.get("RASTRO_FCM_SERVER_KEY", "")
        self._project_id = os.environ.get("RASTRO_FCM_PROJECT_ID", "")
        self._enabled = bool(self._server_key and self._project_id)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def _get_device_tokens(self) -> list[str]:
        """Get all active FCM device tokens from the database."""
        rows = db.query(
            "SELECT token FROM devices WHERE platform = 'fcm' AND is_active = 'true'",
        )
        return [r["token"] for r in rows]

    def send(self, title: str, message: str, priority: str = "medium", metadata: dict[str, Any] | None = None) -> int:
        """Send to all registered FCM devices. Returns count of successful sends."""
        if not self._enabled:
            logger.debug("FCM disabled — set RASTRO_FCM_SERVER_KEY and RASTRO_FCM_PROJECT_ID")
            return 0

        tokens = self._get_device_tokens()
        if not tokens:
            return 0

        url = FCM_SEND_URL.format(project=self._project_id)
        headers = {
            "Authorization": f"Bearer {self._server_key}",
            "Content-Type": "application/json",
        }

        priority_map = {"low": "normal", "medium": "normal", "high": "high", "critical": "high"}
        android_priority = priority_map.get(priority, "normal")

        success = 0
        with httpx.Client() as client:
            for token in tokens:
                payload = {
                    "message": {
                        "token": token,
                        "notification": {"title": title, "body": message},
                        "android": {"priority": android_priority},
                        "data": {"priority": priority, **(metadata or {})},
                    }
                }
                try:
                    resp = client.post(url, json=payload, headers=headers, timeout=10)
                    if resp.is_success:
                        success += 1
                    else:
                        if resp.status_code == 404:
                            _deactivate_token(token)
                        logger.debug("FCM send failed for %s: %s", token[:16], resp.status_code)
                except Exception as exc:
                    logger.debug("FCM request error: %s", exc)

        if success:
            logger.info("FCM sent to %d/%d devices", success, len(tokens))
        return success


def _deactivate_token(token: str) -> None:
    with contextlib.suppress(Exception):
        db.execute("UPDATE devices SET is_active = 'false' WHERE token = ? AND platform = 'fcm'", (token,))


_FCM: FCMAdapter | None = None


def get_fcm_adapter() -> FCMAdapter:
    global _FCM
    if _FCM is None:
        _FCM = FCMAdapter()
    return _FCM
