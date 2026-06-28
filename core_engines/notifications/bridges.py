"""Notification bridges — wires channels, event bus, and persistence together."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("rastro.notifications.bridges")


def register_db_bridge() -> None:
    """Connect NotificationHub -> SQL database persistence."""
    from core_engines.notifications.db_bridge import persist_notification
    from core_engines.notifications.hub import get_hub

    hub = get_hub()
    hub.register_db_bridge(persist_notification)
    logger.info("DB bridge registered on NotificationHub")


def register_desktop_channel() -> None:
    """Register the desktop notification handler on the hub."""
    from core_engines.notifications.hub import get_hub

    def _desktop_handler(type_: str, payload: dict[str, Any]) -> None:
        try:
            from desktop.notifications import send_notification
            priority = payload.get("priority", "medium")
            urgency = "critical" if priority == "critical" else "normal"
            send_notification(
                title=payload.get("title", "Rastro"),
                message=payload.get("message", ""),
                urgency=urgency,
            )
            db_id = payload.get("metadata", {}).get("db_id")
            if db_id:
                from core_engines.notifications.db_bridge import record_delivery
                record_delivery(db_id, "desktop", "sent")
        except Exception as exc:
            logger.debug("Desktop notification handler error: %s", exc)

    hub = get_hub()
    hub.subscribe("desktop", _desktop_handler)
    logger.info("Desktop channel registered on NotificationHub")


def register_email_channel() -> None:
    """Register the email notification handler on the hub."""
    from core_engines.notifications.email import get_email_adapter
    from core_engines.notifications.hub import get_hub

    adapter = get_email_adapter()
    if not adapter.is_enabled:
        logger.info("Email channel skipped — not configured")
        return

    def _email_handler(type_: str, payload: dict[str, Any]) -> None:
        ok = adapter.send(
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            priority=payload.get("priority", "medium"),
            metadata=payload.get("metadata"),
        )
        db_id = payload.get("metadata", {}).get("db_id")
        if db_id:
            from core_engines.notifications.db_bridge import record_delivery
            record_delivery(db_id, "email", "sent" if ok else "failed", None if ok else "send_error")

    hub = get_hub()
    hub.subscribe("email", _email_handler)
    logger.info("Email channel registered on NotificationHub")


def register_fcm_channel() -> None:
    """Register the FCM push notification handler on the hub."""
    from core_engines.notifications.fcm import get_fcm_adapter
    from core_engines.notifications.hub import get_hub

    adapter = get_fcm_adapter()
    if not adapter.is_enabled:
        logger.info("FCM channel skipped — not configured")
        return

    def _fcm_handler(type_: str, payload: dict[str, Any]) -> None:
        count = adapter.send(
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            priority=payload.get("priority", "medium"),
            metadata=payload.get("metadata"),
        )
        db_id = payload.get("metadata", {}).get("db_id")
        if db_id:
            from core_engines.notifications.db_bridge import record_delivery
            record_delivery(db_id, "fcm", "sent" if count else "failed", "no_devices" if not count else None)

    hub = get_hub()
    hub.subscribe("fcm", _fcm_handler)
    logger.info("FCM channel registered on NotificationHub")


def register_event_bridge() -> None:
    """Subscribe to EventBus and create hub notifications from key events."""
    from core_engines.events.event_bus import get_event_bus
    from core_engines.notifications.hub import get_hub
    from core_engines.notifications.push import EVENT_PUSH_MAP

    hub = get_hub()

    def _on_event(event_type: str, **payload: Any) -> None:
        mapping = EVENT_PUSH_MAP.get(event_type)
        if not mapping:
            return

        title = mapping["title"]
        message = payload.get("message") or payload.get("body") or payload.get("description", "")
        priority = payload.get("priority", mapping["priority"])
        dedup_key = f"{event_type}-{payload.get('id', '')}"

        channels = ["web"]
        if priority in ("high", "critical"):
            channels.append("desktop")
        if event_type in ("opportunity:found", "quick_win:detected", "system:error", "system:degraded"):
            channels.append("mobile")

        hub.notify(
            type_=event_type.replace(":", "_"),
            title=title,
            message=str(message)[:500],
            severity=priority,
            priority=priority,
            channels=channels,
            metadata={"event_type": event_type, "linked_type": "event", **payload},
            dedup_key=dedup_key,
        )

    bus = get_event_bus()
    bus.subscribe_async("*", _on_event)
    logger.info("Event -> notification bridge started")


def register_ws_forwarder() -> None:
    """Forward hub notifications to WebSocket clients as notification:new events."""
    from core_engines.notifications.hub import get_hub
    from core_engines.ws.manager import get_ws_manager

    hub = get_hub()
    manager = get_ws_manager()

    def _forward(notif: object) -> None:
        from core_engines.notifications.hub import Notification
        if not isinstance(notif, Notification):
            return
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                manager.broadcast("notification:new", {
                    "id": notif.db_id or notif.id,
                    "type": notif.type,
                    "title": notif.title,
                    "message": notif.message,
                    "severity": notif.severity,
                    "priority": notif.priority,
                    "timestamp": notif.timestamp,
                    "metadata": notif.metadata,
                }),
                loop,
            )
        except RuntimeError:
            logger.warning("Failed to forward notification via WS", exc_info=True)

    hub.add_listener(_forward)
    logger.info("WS forwarder registered on NotificationHub")
