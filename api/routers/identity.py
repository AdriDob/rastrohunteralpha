from fastapi import APIRouter, Request

from core.gateway.schemas import ok, error
from core.identity.identity_manager import get_identity_manager

router = APIRouter(prefix="/api/identity", tags=["identity"])


@router.get("/me")
async def get_identity():
    mgr = get_identity_manager()
    identity = mgr.get_identity()
    if not identity:
        return error("Identity not initialized", version="1.0")
    return ok({
        "user_id": identity.user_id,
        "display_name": identity.display_name,
        "device_count": identity.device_count,
        "preferences": identity.preferences,
    })


@router.post("/preferences")
async def update_preferences(request: Request):
    body = await request.json()
    mgr = get_identity_manager()
    mgr.update_preferences(body)
    return ok({"status": "updated"})


@router.get("/context")
async def get_context():
    mgr = get_identity_manager()
    return ok({"context": mgr.get_context()})


@router.post("/context")
async def update_context(request: Request):
    body = await request.json()
    mgr = get_identity_manager()
    mgr.update_context(body)
    return ok({"status": "updated"})


@router.get("/devices")
async def get_devices():
    mgr = get_identity_manager()
    return ok({"devices": mgr.get_devices(), "count": mgr.get_device_count()})


@router.post("/devices/link")
async def link_device(request: Request):
    body = await request.json()
    device_id = body.get("device_id")
    if not device_id:
        return error("device_id required", version="1.0")
    mgr = get_identity_manager()
    mgr.link_device(device_id, body.get("info", {}))
    return ok({"status": "linked", "device_id": device_id})
