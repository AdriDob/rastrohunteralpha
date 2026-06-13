"""Multi-device state synchronization.

Manages per-device state snapshots with last-write-wins conflict resolution.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

SYNC_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "rastro",
    "sync",
)

# Keys that can be synced across devices
SYNCABLE_KEYS = {
    "last_viewed_target",
    "last_dashboard_tab",
    "filters",
    "preferences",
    "assistant_context",
    "sidebar_state",
    "theme",
    "language",
}


class SyncManager:
    """Manages state synchronization across devices."""

    def __init__(self, persist: bool = True) -> None:
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._global_state: Dict[str, Any] = {}
        self._persist = persist
        if persist:
            os.makedirs(SYNC_DIR, exist_ok=True)
            self._load()

    def _path(self, name: str) -> str:
        return os.path.join(SYNC_DIR, name)

    def _load(self) -> None:
        devices_path = self._path("devices.json")
        state_path = self._path("global.json")
        try:
            if os.path.exists(devices_path):
                with open(devices_path) as f:
                    self._devices = json.load(f)
            if os.path.exists(state_path):
                with open(state_path) as f:
                    self._global_state = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    def _save(self) -> None:
        if not self._persist:
            return
        try:
            with open(self._path("devices.json"), "w") as f:
                json.dump(self._devices, f)
            with open(self._path("global.json"), "w") as f:
                json.dump(self._global_state, f)
        except OSError:
            pass

    def push_state(self, device_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Push state from a device. Last-write-wins per key.

        Returns the merged global state after applying the push.
        """
        now = time.time()
        device_state = self._devices.get(device_id, {"state": {}, "last_sync": 0})

        # Update device record
        for key, value in state.items():
            if key in SYNCABLE_KEYS:
                device_state["state"][key] = {
                    "value": value,
                    "timestamp": now,
                    "device_id": device_id,
                }
                # Last-write-wins: update global state
                self._global_state[key] = {
                    "value": value,
                    "timestamp": now,
                    "device_id": device_id,
                }

        device_state["last_sync"] = now
        self._devices[device_id] = device_state
        self._save()

        return self._build_global_state(device_id)

    def pull_state(self, device_id: str) -> Dict[str, Any]:
        """Pull the current merged state for a device."""
        return self._build_global_state(device_id)

    def resolve_conflict(self, key: str, device_a: str, device_b: str) -> Any:
        """Resolve a conflict between two devices (last-write-wins)."""
        state_a = self._devices.get(device_a, {}).get("state", {}).get(key, {})
        state_b = self._devices.get(device_b, {}).get("state", {}).get(key, {})

        ts_a = state_a.get("timestamp", 0)
        ts_b = state_b.get("timestamp", 0)

        if ts_a >= ts_b:
            return state_a.get("value")
        return state_b.get("value")

    def register_device(self, device_id: str, info: Dict[str, Any]) -> None:
        """Register a new device for sync."""
        if device_id not in self._devices:
            self._devices[device_id] = {
                "state": {},
                "last_sync": time.time(),
                "info": info,
                "registered_at": time.time(),
            }
        else:
            self._devices[device_id]["info"] = {
                **self._devices[device_id].get("info", {}),
                **info,
            }
            self._devices[device_id]["last_sync"] = time.time()
        self._save()

    def get_devices(self) -> List[Dict[str, Any]]:
        return [
            {"device_id": did, "last_sync": d.get("last_sync", 0), "info": d.get("info", {})}
            for did, d in self._devices.items()
        ]

    def _build_global_state(self, device_id: str) -> Dict[str, Any]:
        """Build the response with global state + device-specific state."""
        device_state = self._devices.get(device_id, {}).get("state", {})
        return {
            "global": {
                k: v.get("value")
                for k, v in self._global_state.items()
            },
            "device": {
                k: v.get("value")
                for k, v in device_state.items()
            },
            "device_id": device_id,
            "last_sync": self._devices.get(device_id, {}).get("last_sync", 0),
            "device_count": len(self._devices),
        }


_SYNC: Optional[SyncManager] = None


def get_sync_manager() -> SyncManager:
    global _SYNC
    if _SYNC is None:
        _SYNC = SyncManager()
    return _SYNC
