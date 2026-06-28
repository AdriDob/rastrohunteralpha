"""Push notification system — maps system events to push payloads.

Routes high-signal events through the NotificationHub's 'mobile' channel
and generates minimized push payloads suitable for Web Push / FCM / APNs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("rastro.notifications.push")

EVENT_PUSH_MAP: dict[str, dict[str, Any]] = {
    "opportunity:found": {
        "title": "New Opportunity",
        "priority": "high",
        "icon": "opportunity",
        "ttl": 86400,
    },
    "opportunity:updated": {
        "title": "Opportunity Updated",
        "priority": "medium",
        "icon": "opportunity",
        "ttl": 43200,
    },
    "quick_win:detected": {
        "title": "Quick Win Found",
        "priority": "high",
        "icon": "quick_win",
        "ttl": 86400,
    },
    "report:generated": {
        "title": "Report Ready",
        "priority": "medium",
        "icon": "report",
        "ttl": 43200,
    },
    "system:ready": {
        "title": "System Ready",
        "priority": "low",
        "icon": "system",
        "ttl": 3600,
    },
    "system:degraded": {
        "title": "System Degraded",
        "priority": "critical",
        "icon": "warning",
        "ttl": 7200,
    },
    "system:error": {
        "title": "System Error",
        "priority": "critical",
        "icon": "error",
        "ttl": 7200,
    },
    "contract:warning": {
        "title": "Contract Warning",
        "priority": "medium",
        "icon": "warning",
        "ttl": 43200,
    },
}


@dataclass
class PushPayload:
    title: str
    message: str
    priority: str = "medium"
    icon: str = "default"
    url: str | None = None
    tag: str | None = None
    ttl: int = 86400
    data: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "icon": self.icon,
            "url": self.url,
            "tag": self.tag,
            "data": self.data,
        })


class PushRouter:
    """Maps internal events to push payloads and routes via NotificationHub."""

    def __init__(self, hub=None):
        from core_engines.notifications.hub import get_hub
        self._hub = hub or get_hub()
        self._subscribers: dict[str, list[str]] = {}
        self._vapid_public_key: str | None = None

    def set_vapid_key(self, key: str) -> None:
        self._vapid_public_key = key

    def get_vapid_key(self) -> str | None:
        return self._vapid_public_key

    def event_to_push(self, event_type: str, payload: dict[str, Any]) -> PushPayload | None:
        mapping = EVENT_PUSH_MAP.get(event_type)
        if not mapping:
            return None

        title = mapping["title"]
        message = payload.get("message") or payload.get("body") or payload.get("description", "")
        priority = payload.get("priority", mapping["priority"])
        url = payload.get("url") or payload.get("deep_link")

        if not message:
            message = f"{event_type} event"

        return PushPayload(
            title=title,
            message=str(message)[:200],
            priority=priority,
            icon=mapping["icon"],
            url=url,
            tag=f"{event_type}-{payload.get('id', '')}",
            ttl=mapping.get("ttl", 86400),
            data={"event_type": event_type, **(payload.get("metadata") or {})},
        )

    def subscribe(self, device_id: str, channel: str = "mobile") -> None:
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        if device_id not in self._subscribers[channel]:
            self._subscribers[channel].append(device_id)

    def unsubscribe(self, device_id: str, channel: str = "mobile") -> None:
        if channel in self._subscribers:
            self._subscribers[channel] = [d for d in self._subscribers[channel] if d != device_id]

    def get_subscribers(self, channel: str = "mobile") -> list[str]:
        return self._subscribers.get(channel, [])

    def route_event(self, event_type: str, payload: dict[str, Any]) -> PushPayload | None:
        push = self.event_to_push(event_type, payload)
        if not push:
            return None

        self._hub.notify(
            type_=event_type.replace(":", "_"),
            title=push.title,
            message=push.message,
            severity=push.priority,
            channels=["mobile"],
            metadata={"push": push.to_json(), "url": push.url, "priority": push.priority},
        )
        logger.debug("Routed push: %s — %s", event_type, push.title)
        return push


_PUSH_ROUTER: PushRouter | None = None


def get_push_router() -> PushRouter:
    global _PUSH_ROUTER
    if _PUSH_ROUTER is None:
        _PUSH_ROUTER = PushRouter()
    return _PUSH_ROUTER
