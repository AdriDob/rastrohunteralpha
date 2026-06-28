"""Session persistence for multi-device support.

Stores active sessions, device registrations, and anonymous mode state.
Uses in-memory dict with optional SQLite persistence.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("rastro.auth.session")

from .auth import (
    create_refresh_token,
    create_session_token,
    verify_token,
)

SESSION_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "rastro",
    "sessions",
)


class SessionStore:
    """In-memory session store with optional file persistence."""

    def __init__(self, persist: bool = True) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._devices: dict[str, dict[str, Any]] = {}
        self._persist = persist
        if persist:
            os.makedirs(SESSION_DIR, exist_ok=True)
            self._load()

    def _path(self, name: str) -> str:
        return os.path.join(SESSION_DIR, name)

    def _load(self) -> None:
        path = self._path("sessions.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                    self._sessions = data.get("sessions", {})
                    self._devices = data.get("devices", {})
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load sessions from disk", exc_info=True)

    def _save(self) -> None:
        if not self._persist:
            return
        try:
            with open(self._path("sessions.json"), "w") as f:
                json.dump({"sessions": self._sessions, "devices": self._devices}, f)
        except OSError:
            logger.warning("Failed to save sessions to disk", exc_info=True)

    def create_session(self, device_id: str, meta: dict[str, Any] | None = None) -> dict[str, str]:
        """Create a new session for a device. Returns tokens."""
        token = create_session_token(device_id, meta=meta)
        refresh = create_refresh_token(device_id)
        self._sessions[device_id] = {
            "token": token,
            "refresh": refresh,
            "device_id": device_id,
            "created_at": time.time(),
            "last_seen": time.time(),
            "meta": meta or {},
        }
        self._save()
        return {"token": token, "refresh": refresh, "device_id": device_id}

    def register_device(self, device_id: str, info: dict[str, Any]) -> None:
        """Register or update a device."""
        self._devices[device_id] = {
            **self._devices.get(device_id, {}),
            **info,
            "last_seen": time.time(),
        }
        self._save()

    def get_session(self, device_id: str) -> dict[str, Any] | None:
        return self._sessions.get(device_id)

    def refresh_session(self, device_id: str, refresh_token: str) -> dict[str, str] | None:
        """Refresh a session using a refresh token. Returns new tokens or None."""
        data = verify_token(refresh_token)
        if data is None or data.get("type") != "refresh":
            return None
        if data.get("sub") != device_id:
            return None
        return self.create_session(device_id)

    def remove_session(self, device_id: str) -> None:
        self._sessions.pop(device_id, None)
        self._save()

    def list_devices(self) -> list[dict[str, Any]]:
        return [
            {"device_id": did, **info}
            for did, info in self._devices.items()
        ]

    def list_sessions(self) -> list[dict[str, Any]]:
        return list(self._sessions.values())

    def get_device_count(self) -> int:
        return len(self._devices)


_STORE: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _STORE
    if _STORE is None:
        _STORE = SessionStore()
    return _STORE
