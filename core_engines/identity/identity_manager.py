"""Unified identity system — single logical user across desktop, PWA, and APK.

No external login dependency. Structured for future auth migration.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.identity.device_registry import DeviceRegistry
from core_engines.identity.session_store import SessionStore

logger = logging.getLogger("rastro.identity")

DATA_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "rastro",
    "identity",
)


@dataclass
class UserIdentity:
    user_id: str
    created_at: float = field(default_factory=time.time)
    display_name: str = ""
    preferences: Dict[str, Any] = field(default_factory=dict)
    last_active_context: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=lambda: ["self"])
    api_tokens: List[Dict[str, Any]] = field(default_factory=list)
    device_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "display_name": self.display_name,
            "preferences": self.preferences,
            "last_active_context": self.last_active_context,
            "permissions": self.permissions,
            "device_count": self.device_count,
        }


class IdentityManager:
    """Single logical user manager. Links devices, persists sessions, maintains context."""

    def __init__(self) -> None:
        self._identity: Optional[UserIdentity] = None
        self._device_registry = DeviceRegistry()
        self._session_store = SessionStore()
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()

    # ── Identity lifecycle ────────────────────────────────────────────

    def ensure_identity(self, device_id: Optional[str] = None) -> UserIdentity:
        if self._identity is None:
            stored = self._load_identity_file()
            if stored:
                self._identity = UserIdentity(**stored)
                logger.info("Restored identity: %s", self._identity.user_id)
            else:
                self._identity = UserIdentity(user_id=str(uuid.uuid4()))
                self._save_identity()
                logger.info("Created new identity: %s", self._identity.user_id)

        if device_id:
            self._device_registry.register_device(device_id, self._identity.user_id)
            self._identity.device_count = len(self._device_registry.get_devices(self._identity.user_id))

        return self._identity

    def get_identity(self) -> Optional[UserIdentity]:
        return self._identity

    def update_preferences(self, prefs: Dict[str, Any]) -> None:
        if not self._identity:
            self.ensure_identity()
        self._identity.preferences.update(prefs)
        self._save_identity()

    def update_context(self, context: Dict[str, Any]) -> None:
        if not self._identity:
            self.ensure_identity()
        self._identity.last_active_context.update(context)
        self._identity.last_active_context["updated_at"] = time.time()
        self._save_identity()

    def get_context(self) -> Dict[str, Any]:
        if not self._identity:
            self.ensure_identity()
        return dict(self._identity.last_active_context)

    def get_preferences(self) -> Dict[str, Any]:
        if not self._identity:
            self.ensure_identity()
        return dict(self._identity.preferences)

    def set_display_name(self, name: str) -> None:
        if not self._identity:
            self.ensure_identity()
        self._identity.display_name = name
        self._save_identity()

    # ── Device linking ────────────────────────────────────────────────

    def link_device(self, device_id: str, device_info: Dict[str, Any]) -> None:
        self.ensure_identity(device_id)
        self._device_registry.update_device_info(device_id, device_info)
        self._identity.device_count = len(self._device_registry.get_devices(self._identity.user_id))

    def unlink_device(self, device_id: str) -> None:
        self._device_registry.unregister_device(device_id)

    def get_devices(self) -> List[Dict[str, Any]]:
        if not self._identity:
            return []
        return self._device_registry.get_devices(self._identity.user_id)

    def get_device_count(self) -> int:
        if not self._identity:
            return 0
        return self._identity.device_count

    # ── Session persistence ───────────────────────────────────────────

    def save_session(self, key: str, value: Any) -> None:
        self._session_store.set(key, value)

    def get_session(self, key: str) -> Optional[Any]:
        return self._session_store.get(key)

    def clear_session(self) -> None:
        self._session_store.clear()

    # ── Auth token placeholder ────────────────────────────────────────

    def issue_api_token(self, label: str = "default") -> str:
        token = str(uuid.uuid4())
        if self._identity:
            self._identity.api_tokens.append({
                "token": token,
                "label": label,
                "issued_at": time.time(),
            })
            self._save_identity()
        return token

    def validate_api_token(self, token: str) -> bool:
        if not self._identity:
            return False
        return any(t["token"] == token for t in self._identity.api_tokens)

    # ── Persistence ───────────────────────────────────────────────────

    def _identity_path(self) -> str:
        return os.path.join(DATA_DIR, "identity.json")

    def _load_identity_file(self) -> Optional[Dict[str, Any]]:
        path = self._identity_path()
        try:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
        return None

    def _save_identity(self) -> None:
        if not self._identity:
            return
        try:
            with open(self._identity_path(), "w") as f:
                json.dump(self._identity.to_dict(), f, indent=2)
        except OSError as exc:
            logger.warning("Failed to save identity: %s", exc)

    def _load(self) -> None:
        self.ensure_identity()
        session_path = os.path.join(DATA_DIR, "session.json")
        try:
            if os.path.exists(session_path):
                with open(session_path) as f:
                    data = json.load(f)
                self._session_store._data.update(data)
        except (json.JSONDecodeError, OSError):
            pass

    def to_dict(self) -> Dict[str, Any]:
        if not self._identity:
            return {}
        return {
            **self._identity.to_dict(),
            "devices": self.get_devices(),
            "session_keys": list(self._session_store._data.keys()),
        }


_IDENTITY: Optional[IdentityManager] = None


def get_identity_manager() -> IdentityManager:
    global _IDENTITY
    if _IDENTITY is None:
        _IDENTITY = IdentityManager()
    return _IDENTITY
