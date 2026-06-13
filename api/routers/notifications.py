from typing import Optional

from fastapi import APIRouter, Query, Request

from core.notifications.hub import get_hub, NOTIFICATION_TYPES
from core.gateway.schemas import ok, error

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/hub")
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    type_: Optional[str] = Query(None, alias="type"),
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
        }
        for n in notifications
    ]

    return ok({"notifications": items, "total": len(items)})


@router.post("/preferences")
async def set_notification_preferences(request: Request):
    """Set per-channel notification preferences.

    Body: { "channel": "desktop"|"web"|"mobile", "enabled": bool }
    """
    body = await request.json()
    channel = body.get("channel")
    enabled = body.get("enabled", True)

    valid_channels = ["desktop", "web", "mobile"]
    if channel not in valid_channels:
        return error(f"Invalid channel: {channel}. Valid: {', '.join(valid_channels)}", version="1.0")

    return ok({"channel": channel, "enabled": enabled, "status": "updated"})


@router.get("/types")
async def list_notification_types():
    """List all supported notification types."""
    return ok({"types": NOTIFICATION_TYPES})


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
