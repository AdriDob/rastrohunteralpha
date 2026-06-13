"""License activation and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from core_engines.license import validate_license, is_license_valid
from core_engines.license.store import get_license_store
from core_engines.gateway.schemas import ok, error

router = APIRouter(prefix="/api/license", tags=["license"])


@router.get("/status")
async def license_status():
    valid, reason = is_license_valid()
    store = get_license_store()
    stored = store.load()
    info = {
        "valid": valid,
        "reason": reason,
        "activated": stored is not None,
    }
    if stored:
        info["hardware_id"] = stored["hardware_id"][:8] + "..."
    return ok(info)


@router.post("/activate")
async def activate_license(data: dict):
    key = data.get("key", "").strip()
    if not key:
        return error("License key required", version="1.0")

    valid, reason = validate_license(key)
    if not valid:
        return error(reason, version="1.0")

    return ok({"status": "activated", "key": key[:8] + "..."})


@router.post("/deactivate")
async def deactivate_license():
    store = get_license_store()
    store.clear()
    return ok({"status": "deactivated"})
