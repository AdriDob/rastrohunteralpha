from typing import Optional

from fastapi import APIRouter, Request, Query, Header

from core_engines.auth.auth_manager import get_auth_manager
from core_engines.auth.session_validator import get_session_validator
from core_engines.gateway.rate_limit import get_rate_limiter
from core_engines.gateway.schemas import ok, error

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = get_rate_limiter()


@router.post("/login")
async def login(request: Request):
    body = await request.json()
    device_id = body.get("device_id", "unknown")
    device_info = body.get("device_info", {})

    manager = get_auth_manager()
    result = manager.authenticate(device_id, device_info)

    return ok(result)


@router.post("/refresh")
async def refresh_token(request: Request):
    body = await request.json()
    device_id = body.get("device_id")
    refresh_token = body.get("refresh_token")

    if not device_id or not refresh_token:
        return error("device_id and refresh_token required", version="1.0")

    manager = get_auth_manager()
    result = manager.refresh(device_id, refresh_token)

    if result is None:
        return error("Invalid or expired refresh token", version="1.0")

    return ok(result)


@router.post("/logout")
async def logout(request: Request):
    body = await request.json()
    device_id = body.get("device_id")

    if not device_id:
        return error("device_id required", version="1.0")

    manager = get_auth_manager()
    manager.logout(device_id)

    return ok({"status": "logged_out", "device_id": device_id})


@router.get("/me")
async def get_me(authorization: Optional[str] = Header(None)):
    if not authorization:
        return error("Authorization header required", version="1.0")

    token = authorization.replace("Bearer ", "")
    validator = get_session_validator()
    result = validator.validate(token)

    if not result.valid:
        return error(result.reason or "Invalid session", version="1.0")

    return ok({
        "device_id": result.device_id,
        "user_id": result.user_id,
        "authenticated": True,
    })


@router.post("/validate")
async def validate_session(request: Request):
    body = await request.json()
    token = body.get("token", "")

    if not token:
        return error("token required", version="1.0")

    validator = get_session_validator()
    result = validator.validate(token)

    return ok(result.to_dict())


@router.get("/session")
async def get_session(device_id: str = Query(None)):
    if not device_id:
        return error("device_id query parameter required", version="1.0")

    manager = get_auth_manager()
    session = manager.get_session(device_id)

    if session is None:
        return error("Session not found", version="1.0")

    return ok({
        "device_id": session["device_id"],
        "created_at": session.get("created_at"),
        "last_seen": session.get("last_seen"),
        "meta": session.get("meta", {}),
    })


@router.get("/devices")
async def list_devices():
    manager = get_auth_manager()
    devices = manager.list_devices()
    return ok({"devices": devices, "total": len(devices)})


@router.get("/stats")
async def auth_stats():
    manager = get_auth_manager()
    return ok(manager.get_stats())


@router.post("/secure-token")
async def store_secure_token(request: Request):
    body = await request.json()
    device_id = body.get("device_id")
    token = body.get("token")

    if not device_id or not token:
        return error("device_id and token required", version="1.0")

    manager = get_auth_manager()
    manager.store_secure_token(device_id, token)

    return ok({"status": "stored"})


@router.get("/secure-token")
async def get_secure_token(device_id: str = Query(None)):
    if not device_id:
        return error("device_id query parameter required", version="1.0")

    manager = get_auth_manager()
    token = manager.get_secure_token(device_id)

    if token is None:
        return error("No secure token found", version="1.0")

    return ok({"token": token, "device_id": device_id})
