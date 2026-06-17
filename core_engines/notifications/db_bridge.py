"""Bridge between NotificationHub (in-memory) and SQL notifications table."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from database import db

if TYPE_CHECKING:
    from core_engines.notifications.hub import Notification

logger = logging.getLogger("rastro.notifications.db_bridge")


def persist_notification(notif: Notification) -> None:
    """Persist a hub notification to the SQL notifications table."""
    session = db.SessionLocal()
    try:
        from database.models import Notification as NotificationModel

        row = NotificationModel(
            notification_type=notif.type,
            title=notif.title,
            message=notif.message,
            severity=notif.severity,
            priority=notif.priority,
            linked_type=notif.metadata.get("linked_type") if notif.metadata else None,
            linked_id=notif.metadata.get("linked_id") if notif.metadata else None,
            dedup_key=notif.dedup_key,
        )
        session.add(row)
        session.commit()
        notif.db_id = row.id
        logger.debug("Persisted notification %s → id=%s", notif.id, row.id)
    except Exception as exc:
        session.rollback()
        logger.warning("Failed to persist notification: %s", exc)
    finally:
        session.close()


def record_delivery(notification_id: int, channel: str, status: str = "sent", error: str | None = None) -> None:
    """Record delivery status for a notification channel."""
    from datetime import datetime, timezone

    session = db.SessionLocal()
    try:
        from database.models import DeliveryRecord

        record = DeliveryRecord(
            notification_id=notification_id,
            channel=channel,
            status=status,
            error=error,
            delivered_at=datetime.now(timezone.utc) if status == "sent" else None,
        )
        session.add(record)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.warning("Failed to record delivery: %s", exc)
    finally:
        session.close()
