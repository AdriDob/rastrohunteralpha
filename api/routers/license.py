"""License activation and status endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from core_engines.gateway.schemas import error, ok
from core_engines.license import is_license_valid, validate_license
from core_engines.license.store import get_license_store

logger = logging.getLogger("rastro.api.license")

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
    logger.info("[HW] activate_license: key (truncated) = %s...", key[:12] if len(key) > 12 else key)
    if not key:
        logger.info("[HW] activate_license: no key provided")
        return error("License key required", version="1.0")

    valid, reason = validate_license(key)
    logger.info("[HW] activate_license: validate_license result = (%s, %s)", valid, reason)
    if not valid:
        logger.info("[HW] activate_license: returning activation FAILED: %s", reason)
        return error(reason, version="1.0")

    logger.info("[HW] activate_license: activation SUCCESS")
    return ok({"status": "activated", "key": key[:8] + "..."})


@router.post("/deactivate")
async def deactivate_license():
    store = get_license_store()
    store.clear()
    return ok({"status": "deactivated"})
