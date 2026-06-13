"""TokenService — secure token storage with device binding and expiry."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

TOKEN_STORE_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "rastro",
    "tokens",
)


class TokenService:
    """Persistent secure token store with device binding and automatic expiry."""

    def __init__(self, persist: bool = True) -> None:
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._persist = persist
        if persist:
            os.makedirs(TOKEN_STORE_DIR, exist_ok=True)
            self._load()

    def _path(self) -> str:
        return os.path.join(TOKEN_STORE_DIR, "secure_tokens.json")

    def _load(self) -> None:
        path = self._path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                    self._tokens = data.get("tokens", {})
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        if not self._persist:
            return
        try:
            with open(self._path(), "w") as f:
                json.dump({"tokens": self._tokens}, f)
        except OSError:
            pass

    def store_token(self, device_id: str, token: str, ttl: int = 86400) -> None:
        self._tokens[device_id] = {
            "token": token,
            "device_id": device_id,
            "created_at": time.time(),
            "expires_at": time.time() + ttl,
        }
        self._save()

    def get_token(self, device_id: str) -> Optional[str]:
        entry = self._tokens.get(device_id)
        if entry is None:
            return None
        if entry.get("expires_at", 0) < time.time():
            self._tokens.pop(device_id, None)
            self._save()
            return None
        return entry["token"]

    def revoke_token(self, device_id: str) -> bool:
        if device_id in self._tokens:
            del self._tokens[device_id]
            self._save()
            return True
        return False

    def cleanup_expired(self) -> int:
        now = time.time()
        expired = [k for k, v in self._tokens.items() if v.get("expires_at", 0) < now]
        for k in expired:
            del self._tokens[k]
        if expired:
            self._save()
        return len(expired)

    def list_tokens(self) -> List[Dict[str, Any]]:
        now = time.time()
        result = []
        for device_id, entry in self._tokens.items():
            if entry.get("expires_at", 0) >= now:
                result.append({
                    "device_id": device_id,
                    "created_at": entry.get("created_at"),
                    "expires_at": entry.get("expires_at"),
                })
        return result

    def count(self) -> int:
        return len(self._tokens)


_TOKEN_SERVICE: Optional[TokenService] = None


def get_token_service() -> TokenService:
    global _TOKEN_SERVICE
    if _TOKEN_SERVICE is None:
        _TOKEN_SERVICE = TokenService()
    return _TOKEN_SERVICE
