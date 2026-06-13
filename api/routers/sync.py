from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from core.sync.manager import get_sync_manager
from core.auth.auth import verify_session
from core.gateway.schemas import ok, error

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/push")
async def push_state(request: Request):
    """Push device state to the sync server (last-write-wins)."""
    body = await request.json()
    device_id = body.get("device_id")
    state = body.get("state", {})

    if not device_id:
        return error("device_id required", version="1.0")

    manager = get_sync_manager()
    merged = manager.push_state(device_id, state)

    return ok(merged)


@router.get("/pull")
async def pull_state(device_id: str = Query(None)):
    """Pull the current merged state for a device."""
    if not device_id:
        return error("device_id query parameter required", version="1.0")

    manager = get_sync_manager()
    state = manager.pull_state(device_id)

    return ok(state)


@router.get("/devices")
async def list_sync_devices():
    """List all devices registered for sync."""
    manager = get_sync_manager()
    devices = manager.get_devices()
    return ok({"devices": devices, "total": len(devices)})


@router.post("/register")
async def register_device(request: Request):
    """Register a new device for state synchronization."""
    body = await request.json()
    device_id = body.get("device_id")
    device_info = body.get("device_info", {})

    if not device_id:
        return error("device_id required", version="1.0")

    manager = get_sync_manager()
    manager.register_device(device_id, device_info)

    return ok({"device_id": device_id, "status": "registered"})


@router.post("/session")
async def restore_session(request: Request):
    """Restore session context when a device reconnects."""
    body = await request.json()
    device_id = body.get("device_id")
    token = body.get("token")

    if not device_id:
        return error("device_id required", version="1.0")

    is_valid, payload = verify_session(token or "")
    if not is_valid:
        return error("Invalid token", version="1.0")

    manager = get_sync_manager()
    state = manager.pull_state(device_id)

    # Return session context: last tab, filters, target
    global_state = state.get("global", {})
    return ok({
        "session": {
            "last_dashboard_tab": global_state.get("last_dashboard_tab"),
            "last_viewed_target": global_state.get("last_viewed_target"),
            "filters": global_state.get("filters"),
            "theme": global_state.get("theme"),
            "language": global_state.get("language"),
        },
        "device_id": device_id,
    })
