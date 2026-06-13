"""Centralized Notification Hub.

Routes notifications to registered channels:
  - desktop: system tray notifications
  - web: in-app notification center
  - mobile: push-ready payload (APK/PWA layer)

Notification types:
  - opportunity_detected
  - quick_win_found
  - report_ready
  - system_health_alert
  - assistant_recommendation

Features:
  - Dedup: same type+dedup_key within DEDUP_WINDOW seconds is dropped
  - Priority: every notification has a priority level (low/medium/high/critical)
  - Digest mode: batches notifications into periodic summaries
  - DB bridge: optional persistence callback to SQL notifications table
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("rastro.notifications.hub")

NOTIFICATION_TYPES = [
    "opportunity_detected",
    "quick_win_found",
    "report_ready",
    "system_health_alert",
    "assistant_recommendation",
]

DEDUP_WINDOW = 30  # seconds: same dedup_key within this window is skipped


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


ChannelHandler = Callable[[str, Dict[str, Any]], None]


@dataclass
class Notification:
    """A single notification event."""
    id: str
    type: str
    title: str
    message: str
    severity: str = "info"
    priority: str = "medium"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    channels: List[str] = field(default_factory=lambda: ["web"])
    dedup_key: Optional[str] = None


class NotificationHub:
    """Central notification router. Channels register via subscribe()."""

    def __init__(self) -> None:
        self._channels: Dict[str, List[ChannelHandler]] = {
            "desktop": [],
            "web": [],
            "mobile": [],
        }
        self._history: List[Notification] = []
        self._max_history = 200
        self._digest_mode: bool = False
        self._digest_buffer: List[Notification] = []
        self._dedup_tracker: Dict[Tuple[str, Optional[str]], float] = {}
        self._dedup_window: float = DEDUP_WINDOW
        self._db_bridge: Optional[Callable[[Notification], None]] = None
        self._listeners: List[Callable[[Notification], None]] = []

    def set_digest_mode(self, enabled: bool) -> None:
        """Toggle digest mode. When on, notifications are batched instead of routed live."""
        self._digest_mode = enabled

    def is_digest_mode(self) -> bool:
        return self._digest_mode

    def set_dedup_window(self, seconds: float) -> None:
        self._dedup_window = seconds

    def get_dedup_window(self) -> float:
        return self._dedup_window

    def register_db_bridge(self, callback: Callable[[Notification], None]) -> None:
        """Register a callback that persists notifications to the SQL database."""
        self._db_bridge = callback

    def subscribe(self, channel: str, handler: ChannelHandler) -> None:
        """Register a handler for a notification channel."""
        if channel not in self._channels:
            self._channels[channel] = []
        self._channels[channel].append(handler)
        logger.debug("Handler registered for channel '%s'", channel)

    def unsubscribe(self, channel: str, handler: ChannelHandler) -> None:
        """Remove a handler from a channel."""
        if channel in self._channels:
            self._channels[channel] = [h for h in self._channels[channel] if h != handler]

    def add_listener(self, fn: Callable[[Notification], None]) -> None:
        self._listeners.append(fn)

    def _is_duplicate(self, notif: Notification) -> bool:
        if not notif.dedup_key:
            return False
        key = (notif.type, notif.dedup_key)
        last = self._dedup_tracker.get(key)
        now = time.time()
        if last is not None and (now - last) < self._dedup_window:
            return True
        self._dedup_tracker[key] = now
        return False

    def send(self, notif: Notification) -> Optional[Notification]:
        """Route a notification to all its target channels.
        Returns the notification if sent, None if deduplicated.
        """
        if notif.type not in NOTIFICATION_TYPES:
            logger.warning("Unknown notification type: %s", notif.type)
            notif.type = "system_health_alert"

        if self._is_duplicate(notif):
            logger.debug("Deduped notification: %s / dedup_key=%s", notif.type, notif.dedup_key)
            return None

        self._history.append(notif)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        if self._db_bridge:
            try:
                self._db_bridge(notif)
            except Exception as exc:
                logger.warning("DB bridge error: %s", exc)

        if self._digest_mode:
            self._digest_buffer.append(notif)
            logger.debug("Buffered notification for digest: %s", notif.type)
            return notif

        self._route(notif)
        for fn in self._listeners:
            try:
                fn(notif)
            except Exception:
                pass
        return notif

    def _route(self, notif: Notification) -> None:
        for channel in notif.channels:
            handlers = self._channels.get(channel, [])
            for handler in handlers:
                try:
                    handler(notif.type, {
                        "id": notif.id,
                        "type": notif.type,
                        "title": notif.title,
                        "message": notif.message,
                        "severity": notif.severity,
                        "priority": notif.priority,
                        "timestamp": notif.timestamp,
                        "metadata": notif.metadata,
                    })
                except Exception as exc:
                    logger.warning("Notification handler error on %s: %s", channel, exc)

    def flush_digest(self) -> List[Dict[str, Any]]:
        """Flush buffered notifications and return a digest summary."""
        if not self._digest_buffer:
            return []
        buffer = self._digest_buffer[:]
        self._digest_buffer.clear()

        groups: Dict[str, List[Notification]] = {}
        for n in buffer:
            groups.setdefault(n.type, []).append(n)

        summary = []
        for notif_type, items in groups.items():
            priorities = [n.priority for n in items]
            highest = "critical" if "critical" in priorities else \
                      "high" if "high" in priorities else \
                      "medium" if "medium" in priorities else "low"
            summary.append({
                "type": notif_type,
                "count": len(items),
                "highest_priority": highest,
                "titles": [n.title for n in items[:3]],
                "timestamp": items[-1].timestamp,
            })

        for n in buffer:
            self._route(n)

        return summary

    def notify(
        self,
        type_: str,
        title: str,
        message: str,
        severity: str = "info",
        priority: str = "medium",
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        dedup_key: Optional[str] = None,
    ) -> Optional[Notification]:
        """Convenience: create and send a notification in one call."""
        notif = Notification(
            id=f"{type_}-{int(time.time() * 1000)}",
            type=type_,
            title=title,
            message=message,
            severity=severity,
            priority=priority,
            channels=channels or ["web"],
            metadata=metadata or {},
            dedup_key=dedup_key,
        )
        return self.send(notif)

    def get_history(self, limit: int = 50) -> List[Notification]:
        return self._history[-limit:]

    def get_history_by_type(self, type_: str, limit: int = 20) -> List[Notification]:
        return [n for n in self._history if n.type == type_][-limit:]

    def clear_dedup(self) -> None:
        self._dedup_tracker.clear()

    def get_digest_buffer_size(self) -> int:
        return len(self._digest_buffer)


_HUB: Optional[NotificationHub] = None


def get_hub() -> NotificationHub:
    global _HUB
    if _HUB is None:
        _HUB = NotificationHub()
    return _HUB
