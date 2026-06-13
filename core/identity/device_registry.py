"""Device registry — lightweight device fingerprinting and cross-platform linking.

Tracks devices (desktop, PWA browser, Capacitor APK) per user identity.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rastro.identity.device")

DATA_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "rastro",
    "identity",
)

DEVICE_TTL = 86400 * 90


class DeviceRegistry:
    """Tracks devices linked to a user identity."""

    def __init__(self) -> None:
        self._devices: Dict[str, Dict[str, Any]] = {}
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()

    def register_device(self, device_id: str, user_id: str) -> None:
        now = time.time()
        if device_id in self._devices:
            self._devices[device_id]["last_seen"] = now
            self._devices[device_id]["user_id"] = user_id
        else:
            self._devices[device_id] = {
                "device_id": device_id,
                "user_id": user_id,
                "first_seen": now,
                "last_seen": now,
                "info": {},
                "platform": self._detect_platform(device_id),
            }
        self._save()

    def update_device_info(self, device_id: str, info: Dict[str, Any]) -> None:
        if device_id in self._devices:
            self._devices[device_id]["info"].update(info)
            self._devices[device_id]["last_seen"] = time.time()
            self._save()

    def unregister_device(self, device_id: str) -> None:
        self._devices.pop(device_id, None)
        self._save()

    def get_devices(self, user_id: str) -> List[Dict[str, Any]]:
        now = time.time()
        active = []
        for d in self._devices.values():
            if d.get("user_id") == user_id:
                if now - d.get("last_seen", 0) < DEVICE_TTL:
                    active.append(d)
        return active

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self._devices.get(device_id)

    def get_device_count(self, user_id: str) -> int:
        return len(self.get_devices(user_id))

    def device_exists(self, device_id: str) -> bool:
        return device_id in self._devices

    def cleanup_stale(self) -> int:
        now = time.time()
        stale = [did for did, d in self._devices.items() if now - d.get("last_seen", 0) > DEVICE_TTL]
        for did in stale:
            del self._devices[did]
        if stale:
            self._save()
        return len(stale)

    def _detect_platform(self, device_id: str) -> str:
        if device_id.startswith("desktop-"):
            return "desktop"
        if device_id.startswith("pwa-"):
            return "pwa"
        if device_id.startswith("capacitor-"):
            return "apk"
        return "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "devices": list(self._devices.values()),
            "total": len(self._devices),
        }

    def _path(self) -> str:
        return os.path.join(DATA_DIR, "devices.json")

    def _load(self) -> None:
        try:
            if os.path.exists(self._path()):
                with open(self._path()) as f:
                    data = json.load(f)
                    self._devices = {d["device_id"]: d for d in data.get("devices", [])}
        except (json.JSONDecodeError, OSError):
            pass

    def _save(self) -> None:
        try:
            with open(self._path(), "w") as f:
                json.dump(self.to_dict(), f, indent=2)
        except OSError as exc:
            logger.warning("Failed to save device registry: %s", exc)
