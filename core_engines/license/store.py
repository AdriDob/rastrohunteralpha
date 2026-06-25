"""Persist license key + hardware binding to disk."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from core_engines.license.hardware import get_hardware_id

logger = logging.getLogger("rastro.license.store")

_DIAG_LOG = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Rastro", "license_diagnostic.log",
)

def _append_diag(msg: str) -> None:
    try:
        os.makedirs(os.path.dirname(_DIAG_LOG), exist_ok=True)
        with open(_DIAG_LOG, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass

def _get_license_file() -> Path:
    from core_engines.platform.system import get_data_dir
    path = get_data_dir() / "license.json"
    logger.info("LICENSE PATH = %s", path)
    logger.info("LICENSE EXISTS = %s", path.exists())
    _append_diag(f"[STORE-DIAG] _get_license_file() → {path}")
    _append_diag(f"[STORE-DIAG]   exists={path.exists()}")
    if path.exists():
        _append_diag(f"[STORE-DIAG]   size={path.stat().st_size}")
    return path


class LicenseStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or _get_license_file()
        _append_diag(f"[STORE-DIAG] LicenseStore._path = {self._path}")

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
            _append_diag(f"[STORE-DIAG] load() → file NOT FOUND at {self._path}")
            return None
        try:
            content = self._path.read_text()
            data = json.loads(content)
            _append_diag(f"[STORE-DIAG] load() → FOUND at {self._path}")
            _append_diag(f"[STORE-DIAG]   content: {content}")
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load license store: %s", exc)
            _append_diag(f"[STORE-DIAG] load() → ERROR: {exc}")
            return None

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
            _append_diag(f"[STORE-DIAG] clear() → deleted {self._path}")

    @property
    def is_activated(self) -> bool:
        data = self.load()
        if not data:
            _append_diag(f"[STORE-DIAG] is_activated → False (no data)")
            return False
        stored_hw = data.get("hardware_id", "")
        current_hw = get_hardware_id()
        _append_diag(f"[STORE-DIAG] is_activated: stored_hw={stored_hw} current_hw={current_hw}")
        if stored_hw and stored_hw != current_hw:
            _append_diag(f"[STORE-DIAG] is_activated → auto-heal: {stored_hw} → {current_hw}")
            self.save(data.get("license_key", ""), current_hw)
        _append_diag(f"[STORE-DIAG] is_activated → True")
        return True


_store: Optional[LicenseStore] = None


def get_license_store() -> LicenseStore:
    global _store
    if _store is None:
        _store = LicenseStore()
    return _store
