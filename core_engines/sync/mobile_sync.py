"""Lightweight mobile state sync — minimal payload, last-write-wins.

Synchronizes only what a mobile user cares about:
- last viewed target / opportunity
- assistant context summary
- UI preferences (theme, language)
- notification read states

No raw pipeline data, no full tables, no heavy joins.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("rastro.sync.mobile")

MOBILE_SYNC_KEYS = {
    "last_viewed_target",
    "last_viewed_opportunity",
    "last_dashboard_tab",
    "assistant_context",
    "assistant_context_memory",
    "theme",
    "language",
    "notification_read_state",
    "pending_actions",
    "device_class",
    "daily_briefing_seen",
}

CONTINUITY_KEYS = {
    "last_viewed_target",
    "last_viewed_opportunity",
    "last_dashboard_tab",
    "assistant_context_memory",
    "pending_actions",
}


@dataclass
class MobileSyncSnapshot:
    device_id: str
    timestamp: float = field(default_factory=time.time)
    state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "state": self.state,
        }


class MobileSyncManager:
    """Thin sync manager for mobile state — delegates full device sync to SyncManager."""

    def __init__(self) -> None:
        self._snapshots: dict[str, MobileSyncSnapshot] = {}
        self._merged: dict[str, Any] = {}
        self._last_cleanup = time.time()

    def push(self, device_id: str, state: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        filtered = {k: v for k, v in state.items() if k in MOBILE_SYNC_KEYS}
        self._snapshots[device_id] = MobileSyncSnapshot(
            device_id=device_id,
            timestamp=now,
            state=filtered,
        )
        for key, value in filtered.items():
            self._merged[key] = {"value": value, "timestamp": now, "device_id": device_id}
        self._cleanup()
        return self.pull(device_id)

    def pull(self, device_id: str) -> dict[str, Any]:
        device_state = self._snapshots.get(device_id)
        return {
            "global": {k: v.get("value") for k, v in self._merged.items()},
            "device": dict(device_state.state) if device_state else {},
            "device_id": device_id,
            "timestamp": time.time(),
        }

    def resolve(self, key: str, device_a: str, device_b: str) -> Any:
        a = self._snapshots.get(device_a)
        b = self._snapshots.get(device_b)
        ts_a = a.timestamp if a else 0
        ts_b = b.timestamp if b else 0
        entry = self._merged.get(key)
        if not entry:
            return None
        if ts_a >= ts_b:
            return a.state.get(key) if a else None
        return b.state.get(key) if b else None

    def get_all_keys(self) -> dict[str, Any]:
        return {k: v.get("value") for k, v in self._merged.items()}

    def get_continuity_context(self, device_id: str) -> dict[str, Any]:
        context = {}
        for key in CONTINUITY_KEYS:
            entry = self._merged.get(key)
            if entry:
                context[key] = entry.get("value")
        device = self._snapshots.get(device_id)
        if device:
            for key in CONTINUITY_KEYS:
                if key in device.state:
                    context[f"device_{key}"] = device.state[key]
        return context

    def _cleanup(self, max_age: float = 86400 * 30) -> None:
        now = time.time()
        if now - self._last_cleanup < 3600:
            return
        self._last_cleanup = now
        cutoff = now - max_age
        self._snapshots = {
            did: snap
            for did, snap in self._snapshots.items()
            if snap.timestamp >= cutoff
        }


_MOBILE_SYNC: MobileSyncManager | None = None


def get_mobile_sync() -> MobileSyncManager:
    global _MOBILE_SYNC
    if _MOBILE_SYNC is None:
        _MOBILE_SYNC = MobileSyncManager()
    return _MOBILE_SYNC
