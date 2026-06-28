from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from core_engines.settings.service import (
    RastroMode,
    get_all_settings,
    get_mode,
    get_platform_config,
    set_mode,
    set_platform_config,
)

router = APIRouter(prefix="/api/settings/runtime", tags=["settings"])


@router.get("")
def get_runtime_settings() -> dict[str, Any]:
    return get_all_settings()


@router.get("/mode")
def get_mode_setting() -> dict[str, str]:
    return {"mode": get_mode().value}


@router.put("/mode")
def set_mode_setting(body: dict[str, str]) -> dict[str, str]:
    mode = body.get("mode", "manual")
    try:
        validated = RastroMode(mode)
    except ValueError:
        validated = RastroMode.MANUAL
    set_mode(validated)
    return {"mode": validated.value, "status": "ok"}


@router.get("/platforms")
def get_platform_settings() -> dict[str, dict[str, Any]]:
    from core_engines.settings.service import get_all_platform_configs
    return get_all_platform_configs()


@router.get("/platforms/{platform_id}")
def get_single_platform(platform_id: str) -> dict[str, Any]:
    return get_platform_config(platform_id)


@router.put("/platforms/{platform_id}")
def update_platform(platform_id: str, body: dict[str, Any]) -> dict[str, Any]:
    set_platform_config(platform_id, body)
    return {**get_platform_config(platform_id), "status": "ok"}
