"""Persist license key + hardware binding to disk."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from core_engines.license.hardware import get_hardware_id

logger = logging.getLogger("rastro.license.store")

def _get_license_file() -> Path:
    from core_engines.platform.system import get_data_dir
    return get_data_dir() / "license.json"


class LicenseStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or _get_license_file()

    def save(self, license_key: str, hardware_id: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "license_key": license_key,
            "hardware_id": hardware_id,
            "activated_at": __import__("time").time(),
        }
        self._path.write_text(json.dumps(data, indent=2))

    def load(self) -> Optional[dict]:
        if not self._path.exists():
            return None
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load license store: %s", exc)
            return None

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()

    @property
    def is_activated(self) -> bool:
        data = self.load()
        if not data:
            return False
        stored_hw = data.get("hardware_id", "")
        if stored_hw and stored_hw != get_hardware_id():
            logger.warning("Hardware mismatch — license invalidated")
            self.clear()
            return False
        return True


_store: Optional[LicenseStore] = None


def get_license_store() -> LicenseStore:
    global _store
    if _store is None:
        _store = LicenseStore()
    return _store
