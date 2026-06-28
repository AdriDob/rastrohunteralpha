from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core_engines.ai.provider import PROVIDER_CATALOG, get_registry

router = APIRouter(prefix="/api/settings/ai", tags=["settings-ai"])


@router.get("/providers")
def list_providers():
    registry = get_registry()
    return {"providers": registry.list_providers()}


@router.get("/config")
def get_config():
    registry = get_registry()
    provider = registry.get_provider()
    cfg = registry._load_config()
    return {
        "provider_type": cfg.get("provider_type", "ollama"),
        "host": cfg.get("host", ""),
        "model": cfg.get("model", "") or cfg.get("llm_model", ""),
        "api_base": cfg.get("api_base", ""),
        "active_provider": provider.name,
        "available": provider.is_available(),
    }


class AIConfigUpdate(BaseModel):
    provider_type: str = "ollama"
    host: str = ""
    model: str = ""
    api_key: str = ""
    api_base: str = ""


@router.put("/config")
def update_config(body: AIConfigUpdate):
    valid_ids = {s.id for s in PROVIDER_CATALOG}
    if body.provider_type not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Invalid provider. Choose from: {', '.join(valid_ids)}")

    updates = {"provider_type": body.provider_type}
    if body.provider_type == "ollama":
        updates["host"] = body.host or "http://localhost:11434"
        updates["model"] = body.model or "qwen2.5-coder:7b"
    elif body.provider_type == "openai":
        updates["api_base"] = body.api_base or "https://api.openai.com/v1"
        updates["llm_model"] = body.model or "gpt-4o-mini"
        if body.api_key:
            updates["api_key"] = body.api_key

    registry = get_registry()
    provider = registry.set_config(updates)
    return {
        "status": "ok",
        "active_provider": provider.name,
        "available": provider.is_available(),
    }
