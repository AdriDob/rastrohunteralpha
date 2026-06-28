from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from core_engines.tracking.service import handle_webhook_callback

logger = logging.getLogger("rastro.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

SUPPORTED_PLATFORMS = ["hackerone", "bugcrowd", "intigriti", "yeswehack", "synack"]


@router.post("/{platform}")
async def platform_webhook(platform: str, request: Request):
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from None

    external_id = body.get("external_id", body.get("id", ""))
    status = body.get("status", body.get("state", "unknown"))
    extra = {
        "reward": body.get("reward"),
        "severity": body.get("severity"),
        "comment": body.get("comment", ""),
    }

    if not external_id:
        raise HTTPException(status_code=400, detail="Missing external_id")

    result = handle_webhook_callback(platform, external_id, status, extra)
    if "error" in result:
        logger.warning("Webhook error for %s/%s: %s", platform, external_id, result["error"])
        return {"status": "error", "detail": result["error"]}

    logger.info(
        "Webhook processed: %s/%s -> %s (report %s)",
        platform, external_id, status, result.get("report_id"),
    )
    return {"status": "ok", "data": result}
