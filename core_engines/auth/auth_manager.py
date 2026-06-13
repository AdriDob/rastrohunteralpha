"""AuthManager — unified auth facade with device binding, session lifecycle."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from core.auth.auth import (
    create_session_token,
    create_refresh_token,
    verify_token,
    verify_session,
    TOKEN_TTL,
)
from core.auth.session import get_session_store, SessionStore
from core.auth.token_service import get_token_service, TokenService

logger = logging.getLogger("rastro.auth.manager")


class AuthManager:
    """Unified auth facade — wraps token creation, device binding, session lifecycle."""

    def __init__(self) -> None:
        self._store: SessionStore = get_session_store()
        self._token_service: TokenService = get_token_service()

    def authenticate(self, device_id: str, device_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        existing = self._store.get_session(device_id)
        if existing:
            token = existing.get("token", "")
            data = verify_token(token)
            if data is not None:
                self._store.register_device(device_id, device_info or {})
                self._store._sessions[device_id]["last_seen"] = time.time()
                self._store._save()
                return {
                    "token": token,
                    "refresh": existing.get("refresh", ""),
                    "device_id": device_id,
                    "user_id": data.get("sub", "local"),
                    "existing": True,
                }

        result = self._store.create_session(device_id, meta=device_info)
        self._store.register_device(device_id, device_info or {})
        result["user_id"] = "local"
        result["existing"] = False
        return result

    def validate(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        return verify_session(token)

    def refresh(self, device_id: str, refresh_token: str) -> Optional[Dict[str, str]]:
        return self._store.refresh_session(device_id, refresh_token)

    def logout(self, device_id: str) -> bool:
        self._store.remove_session(device_id)
        return True

    def validate_device_binding(self, token: str, device_id: str) -> bool:
        data = verify_token(token)
        if data is None:
            return False
        return data.get("sub") == device_id

    def get_session(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get_session(device_id)

    def list_devices(self) -> List[Dict[str, Any]]:
        return self._store.list_devices()

    def get_device_count(self) -> int:
        return self._store.get_device_count()

    def list_sessions(self) -> List[Dict[str, Any]]:
        return self._store.list_sessions()

    def get_secure_token(self, device_id: str) -> Optional[str]:
        return self._token_service.get_token(device_id)

    def store_secure_token(self, device_id: str, token: str, ttl: int = TOKEN_TTL) -> None:
        self._token_service.store_token(device_id, token, ttl)

    def revoke_secure_token(self, device_id: str) -> bool:
        return self._token_service.revoke_token(device_id)

    def cleanup_expired_tokens(self) -> int:
        return self._token_service.cleanup_expired()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "sessions": len(self._store.list_sessions()),
            "devices": self._store.get_device_count(),
            "stored_tokens": self._token_service.count(),
        }


_MANAGER: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = AuthManager()
    return _MANAGER
