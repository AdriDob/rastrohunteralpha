from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core_engines.target_auth.identity_manager import get_identity_manager
from core_engines.target_auth.session_manager import get_session_manager
from core_engines.gateway.schemas import ok, error

router = APIRouter(prefix="/api/targets/{target_id}/identities", tags=["targets"])

manager = get_identity_manager()
session_manager = get_session_manager()


@router.get("")
def list_identities(target_id: int):
    items = manager.get_identities(target_id)
    return ok(items)


@router.get("/{identity_id}")
def get_identity(target_id: int, identity_id: int):
    item = manager.get_identity(identity_id)
    if not item:
        raise HTTPException(status_code=404, detail="Identity not found")
    return ok(item)


@router.post("")
def create_identity(target_id: int, body: dict):
    label = body.get("label", "Default")
    auth_type = body.get("auth_type", "none")
    is_baseline = body.get("is_baseline", False)

    item = manager.create_identity(
        target_id=target_id,
        label=label,
        auth_type=auth_type,
        is_baseline=is_baseline,
        username=body.get("username"),
        password=body.get("password"),
        token=body.get("token"),
        api_key=body.get("api_key"),
        cookies=body.get("cookies"),
        login_url=body.get("login_url"),
        login_params=body.get("login_params"),
    )
    return ok(item)


@router.put("/{identity_id}")
def update_identity(target_id: int, identity_id: int, body: dict):
    item = manager.update_identity(identity_id, **body)
    if not item:
        raise HTTPException(status_code=404, detail="Identity not found")
    return ok(item)


@router.delete("/{identity_id}")
def delete_identity(target_id: int, identity_id: int):
    if manager.delete_identity(identity_id):
        return ok({"deleted": True})
    raise HTTPException(status_code=404, detail="Identity not found")


@router.post("/{identity_id}/login")
def login_identity(target_id: int, identity_id: int):
    result = session_manager.login(identity_id)
    if result.get("error"):
        return error(result["error"], version="1.0")
    return ok({"status": "logged_in", "token_preview": (result.get("token") or "")[:16] + "..." if result.get("token") else None})


@router.get("/{identity_id}/session")
def session_status(target_id: int, identity_id: int):
    status = session_manager.get_session_status(identity_id)
    return ok(status)


@router.delete("/{identity_id}/session")
def logout_identity(target_id: int, identity_id: int):
    session_manager.invalidate_session(identity_id)
    return ok({"status": "logged_out"})
