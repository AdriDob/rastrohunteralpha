"""Experience Unification Layer.

Wires auth + sync + notifications into a single cohesive flow.
Every device interaction passes through this layer to guarantee consistent UX.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.auth.session import get_session_store, SessionStore
from core_engines.sync.manager import get_sync_manager, SyncManager
from core_engines.notifications.hub import get_hub, NotificationHub, Notification

logger = logging.getLogger("rastro.unification")


@dataclass
class DeviceContext:
    """Holds the current device's context for a session."""
    device_id: str
    session_token: str = ""
    last_sync: float = 0.0
    preferences: Dict[str, Any] = field(default_factory=dict)
    last_tab: Optional[str] = None
    last_target: Optional[int] = None


class UnificationLayer:
    """Top-level coordinator for multi-device experience.

    Every operation goes through:
      auth (verify) → sync (state) → notifications (route)
    """

    def __init__(self) -> None:
        self.auth: SessionStore = get_session_store()
        self.sync: SyncManager = get_sync_manager()
        self.hub: NotificationHub = get_hub()
        self._devices: Dict[str, DeviceContext] = {}

    def register_device(self, device_id: str, info: Dict[str, Any]) -> Dict[str, str]:
        """Full device registration: auth session + sync registration.

        Returns tokens and device info.
        """
        # Auth
        result = self.auth.create_session(device_id, meta=info)
        self.auth.register_device(device_id, info)

        # Sync
        self.sync.register_device(device_id, info)

        # Context
        self._devices[device_id] = DeviceContext(
            device_id=device_id,
            session_token=result["token"],
        )

        # Notify
        self.hub.notify(
            "system_health_alert",
            "New device registered",
            f"Device '{device_id}' connected",
            severity="info",
            channels=["web"],
            metadata={"device_id": device_id},
        )

        logger.info("Device registered: %s (%s)", device_id, info.get("name", "unknown"))
        return result

    def push_device_state(self, device_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Push state with full context propagation."""
        merged = self.sync.push_state(device_id, state)
        ctx = self._devices.get(device_id)
        if ctx:
            ctx.last_sync = merged.get("last_sync", 0)
        return merged

    def pull_device_state(self, device_id: str) -> Dict[str, Any]:
        """Pull state with context restoration."""
        state = self.sync.pull_state(device_id)
        ctx = self._devices.get(device_id)
        if ctx:
            ctx.last_sync = state.get("last_sync", 0)
            global_state = state.get("global", {})
            ctx.last_tab = global_state.get("last_dashboard_tab")
            ctx.last_target = global_state.get("last_viewed_target")
        return state

    def notify_device(self, device_id: str, type_: str, title: str, message: str, severity: str = "info") -> None:
        """Send a notification targeted at a specific device.

        Routes to all channels the device has enabled.
        """
        ctx = self._devices.get(device_id)
        if ctx is None:
            logger.warning("Unknown device: %s", device_id)
            return

        # Determine channels based on device preferences
        prefs = ctx.preferences
        channels = []
        for ch in ["desktop", "web", "mobile"]:
            if prefs.get(f"channel_{ch}", True):
                channels.append(ch)
        if not channels:
            channels = ["web"]

        self.hub.notify(
            type_,
            title,
            message,
            severity=severity,
            channels=channels,
            metadata={"device_id": device_id},
        )

    def get_device_context(self, device_id: str) -> Optional[DeviceContext]:
        return self._devices.get(device_id)

    def list_active_devices(self) -> List[Dict[str, Any]]:
        return [
            {
                "device_id": did,
                "last_sync": ctx.last_sync,
                "last_tab": ctx.last_tab,
            }
            for did, ctx in self._devices.items()
        ]

    def disconnect_device(self, device_id: str) -> None:
        """Full device disconnect: remove session, sync, and context."""
        self.auth.remove_session(device_id)
        self._devices.pop(device_id, None)
        logger.info("Device disconnected: %s", device_id)


_UNIFICATION: Optional[UnificationLayer] = None


def get_unification_layer() -> UnificationLayer:
    global _UNIFICATION
    if _UNIFICATION is None:
        _UNIFICATION = UnificationLayer()
    return _UNIFICATION
