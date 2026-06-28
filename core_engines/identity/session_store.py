"""Session persistence — lightweight key-value store for cross-device session continuity.

Backed by JSON file. No DB dependency.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("rastro.identity.session")

DATA_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "rastro",
    "identity",
)


class SessionStore:
    """Persistent session key-value store. Survives restarts."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()

    def set(self, key: str, value: Any) -> None:
        self._data[key] = {"value": value, "updated_at": time.time()}
        self._save()

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry:
            return entry.get("value")
        return None

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._save()

    def clear(self) -> None:
        self._data.clear()
        self._save()

    def keys(self) -> list:
        return list(self._data.keys())

    def get_all(self) -> dict[str, Any]:
        return {k: v.get("value") for k, v in self._data.items()}

    def _path(self) -> str:
        return os.path.join(DATA_DIR, "session.json")

    def _load(self) -> None:
        try:
            if os.path.exists(self._path()):
                with open(self._path()) as f:
                    self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load session store from disk", exc_info=True)

    def _save(self) -> None:
        try:
            with open(self._path(), "w") as f:
                json.dump(self._data, f, indent=2)
        except OSError as exc:
            logger.warning("Failed to save session: %s", exc)
