
from fastapi import APIRouter, Query, Request

from core_engines.gateway.schemas import error, ok
from core_engines.notifications.hub import NOTIFICATION_TYPES, get_hub
from database import db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/hub")
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    type_: str | None = Query(None, alias="type"),
):
    """Get recent notifications from the hub."""
    hub = get_hub()

    if type_:
        if type_ not in NOTIFICATION_TYPES:
            return error(f"Unknown notification type: {type_}. Valid: {', '.join(NOTIFICATION_TYPES)}", version="1.0")
        notifications = hub.get_history_by_type(type_, limit=limit)
    else:
        notifications = hub.get_history(limit=limit)

    items = [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "severity": n.severity,
            "priority": n.priority,
            "timestamp": n.timestamp,
            "metadata": n.metadata,
            "db_id": n.db_id,
        }
        for n in notifications
    ]

    return ok({"notifications": items, "total": len(items)})


@router.post("/preferences")
async def set_notification_preferences(request: Request):
    """Set per-channel notification preferences.
    Persisted to the investigator profile.

    Body: { "channel": "desktop"|"web"|"mobile"|"email"|"fcm", "enabled": bool }
    """
    body = await request.json()
    channel = body.get("channel")
    enabled = body.get("enabled", True)

    valid_channels = ["desktop", "web", "mobile", "email", "fcm"]
    if channel not in valid_channels:
        return error(f"Invalid channel: {channel}. Valid: {', '.join(valid_channels)}", version="1.0")

    try:
        from core_engines.learning.profile import get_profile_service
        profile = get_profile_service()
        prefs = profile.get_stats().get("notification_preferences", {})
        prefs[f"channel_{channel}"] = enabled

        session = db.SessionLocal()
        try:
            from core_engines.learning.profile import InvestigatorProfile
            row = session.query(InvestigatorProfile).first()
            if row:
                row.notification_preferences = prefs
                session.commit()
        finally:
            session.close()

        return ok({"channel": channel, "enabled": enabled, "status": "updated"})
    except Exception as exc:
        return error(str(exc), version="1.0")


@router.get("/preferences")
async def get_notification_preferences():
    """Get current notification channel preferences."""
    try:
        from core_engines.learning.profile import get_profile_service
        profile = get_profile_service()
        prefs = profile.get_stats().get("notification_preferences", {})
        return ok({"preferences": prefs})
    except Exception as exc:
        return error(str(exc), version="1.0")


@router.get("/types")
async def list_notification_types():
    """List all supported notification types."""
    return ok({"types": NOTIFICATION_TYPES})


# ── Device Registration ──────────────────────────────────────────────


@router.post("/devices")
async def register_device(request: Request):
    """Register a device for push notifications.

    Body: { "platform": "fcm"|"apns"|"webpush", "token": "...", "name": "optional" }
    """
    body = await request.json()
    platform = body.get("platform")
    token = body.get("token")
    name = body.get("name")

    if platform not in ("fcm", "apns", "webpush"):
        return error(f"Invalid platform: {platform}", version="1.0")
    if not token:
        return error("token is required", version="1.0")

    try:
        existing = db.query(
            "SELECT id FROM devices WHERE platform = ? AND token = ?",
            (platform, token),
        )
        if existing:
            db.execute(
                "UPDATE devices SET name = ?, is_active = 'true', updated_at = CURRENT_TIMESTAMP WHERE platform = ? AND token = ?",
                (name, platform, token),
            )
        else:
            db.execute(
                "INSERT INTO devices (platform, token, name) VALUES (?, ?, ?)",
                (platform, token, name),
            )
        return ok({"status": "registered", "platform": platform})
    except Exception as exc:
        return error(str(exc), version="1.0")


@router.delete("/devices/{token}")
async def unregister_device(token: str):
    """Unregister a device by push token."""
    try:
        db.execute("UPDATE devices SET is_active = 'false' WHERE token = ?", (token,))
        return ok({"status": "unregistered"})
    except Exception as exc:
        return error(str(exc), version="1.0")


@router.get("/devices")
async def list_devices():
    """List all registered push devices."""
    try:
        rows = db.query(
            "SELECT id, platform, token, name, is_active, created_at FROM devices ORDER BY created_at DESC",
        )
        return ok({"devices": [dict(r) for r in rows]})
    except Exception as exc:
        return error(str(exc), version="1.0")


# ── Delivery Status ──────────────────────────────────────────────────


@router.get("/delivery")
async def get_delivery_records(limit: int = Query(50, ge=1, le=200)):
    """Get recent delivery records."""
    try:
        rows = db.query(
            """SELECT dr.id, dr.notification_id, dr.channel, dr.status,
                      dr.error, dr.delivered_at, dr.created_at,
                      n.notification_type, n.title
               FROM delivery_records dr
               LEFT JOIN notifications n ON n.id = dr.notification_id
               ORDER BY dr.created_at DESC LIMIT ?""",
            (limit,),
        )
        return ok({"records": [dict(r) for r in rows]})
    except Exception as exc:
        return error(str(exc), version="1.0")


# ── Digest & Dedup Intelligence ───────────────────────────────────────


@router.get("/digest")
async def get_digest():
    """Flush and return aggregated digest of buffered notifications."""
    hub = get_hub()
    summary = hub.flush_digest()
    return ok({"digest": summary, "digest_mode": hub.is_digest_mode()})


@router.post("/digest/toggle")
async def toggle_digest(request: Request):
    """Toggle digest mode on/off. Body: { "enabled": bool }"""
    body = await request.json()
    enabled = body.get("enabled", True)
    hub = get_hub()
    hub.set_digest_mode(enabled)
    return ok({"digest_mode": enabled, "status": "updated"})


@router.get("/dedup-config")
async def get_dedup_config():
    """Return current dedup window configuration."""
    hub = get_hub()
    return ok({
        "dedup_window_seconds": hub.get_dedup_window(),
        "digest_buffer_size": hub.get_digest_buffer_size(),
    })


@router.post("/dedup/clear")
async def clear_dedup():
    """Clear the dedup tracker (force re-delivery of next notification)."""
    hub = get_hub()
    hub.clear_dedup()
    return ok({"status": "cleared"})
