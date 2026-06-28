import logging

from fastapi import APIRouter, Request

from core_engines.gateway.schemas import error, ok
from core_engines.identity_vault import get_identity_vault
from core_engines.settings.service import get_setting, set_setting

logger = logging.getLogger("rastro.identity_center")
router = APIRouter(prefix="/api/identity-center", tags=["identity_center"])

PLATFORMS = ["hackerone", "bugcrowd", "intigriti", "yeswehack", "synack"]

PLATFORM_MODE_OPTIONS = ["manual", "prepare", "automatic"]

WALLET_KEYS = ["usdc", "binance", "takenos", "public"]


def _platform_status(provider: str) -> dict:
    vault = get_identity_vault()
    account = vault.get_account(provider) or {}
    health = vault.check_session_health(provider)
    config = get_setting(f"platform.{provider}", {})
    return {
        "provider": provider,
        "connected": account.get("has_credentials", False) and health.get("connected", False),
        "has_token": account.get("has_credentials", False),
        "last_sync": account.get("last_checked", ""),
        "mode": config.get("mode", "manual"),
        "email": account.get("email", ""),
    }


@router.get("")
async def get_identity_center():
    platforms = [_platform_status(p) for p in PLATFORMS]
    email = get_setting("identity.email", {"primary": "", "secondary": ""})
    wallets = get_setting("identity.wallets", {k: "" for k in WALLET_KEYS})
    never_submit = get_setting("rastro.never_submit_without_approval", True)
    return ok({
        "platforms": platforms,
        "email": email,
        "wallets": wallets,
        "never_submit_without_approval": never_submit,
    })


@router.post("/platform/{provider}/connect")
async def connect_platform(provider: str, request: Request):
    if provider not in PLATFORMS:
        return error(f"Unknown platform: {provider}", version="1.0")
    body = await request.json()
    token = body.get("token", "")
    email = body.get("email", "")
    password = body.get("password", "")
    vault = get_identity_vault()
    vault.store_credentials(provider, email=email, token=token, password=password)
    vault.update_session_state(provider, "connected")
    vault.update_health(provider, "ok")
    logger.info("[IDENTITY] Platform %s connected (email=%s)", provider, email)
    return ok({"status": "connected", "provider": provider})


@router.post("/platform/{provider}/disconnect")
async def disconnect_platform(provider: str):
    if provider not in PLATFORMS:
        return error(f"Unknown platform: {provider}", version="1.0")
    vault = get_identity_vault()
    vault.update_session_state(provider, "disconnected")
    vault.update_health(provider, "unknown")
    logger.info("[IDENTITY] Platform %s disconnected", provider)
    return ok({"status": "disconnected", "provider": provider})


@router.post("/platform/{provider}/mode")
async def set_platform_mode(provider: str, request: Request):
    if provider not in PLATFORMS:
        return error(f"Unknown platform: {provider}", version="1.0")
    body = await request.json()
    mode = body.get("mode", "manual")
    if mode not in PLATFORM_MODE_OPTIONS:
        return error(f"Invalid mode: {mode}", version="1.0")
    config = get_setting(f"platform.{provider}", {})
    config["mode"] = mode
    set_setting(f"platform.{provider}", config)
    return ok({"status": "updated", "provider": provider, "mode": mode})


@router.post("/platform/{provider}/remove")
async def remove_platform(provider: str):
    if provider not in PLATFORMS:
        return error(f"Unknown platform: {provider}", version="1.0")
    vault = get_identity_vault()
    vault.remove_credentials(provider)
    logger.info("[IDENTITY] Platform %s credentials removed", provider)
    return ok({"status": "removed", "provider": provider})


@router.post("/email")
async def set_email(request: Request):
    body = await request.json()
    primary = body.get("primary", "")
    secondary = body.get("secondary", "")
    current = get_setting("identity.email", {})
    if primary:
        current["primary"] = primary
    if secondary:
        current["secondary"] = secondary
    set_setting("identity.email", current)
    logger.info("[IDENTITY] Email updated (primary=%s)", primary)
    return ok({"status": "updated", "email": current})


@router.post("/wallets")
async def set_wallets(request: Request):
    body = await request.json()
    current = get_setting("identity.wallets", {k: "" for k in WALLET_KEYS})
    for key in WALLET_KEYS:
        if key in body:
            current[key] = body[key]
    set_setting("identity.wallets", current)
    return ok({"status": "updated", "wallets": current})


@router.post("/never-submit")
async def set_never_submit(request: Request):
    body = await request.json()
    enabled = body.get("enabled", True)
    set_setting("rastro.never_submit_without_approval", enabled)
    logger.info("[IDENTITY] never_submit_without_approval set to %s", enabled)
    return ok({"status": "updated", "never_submit_without_approval": enabled})
