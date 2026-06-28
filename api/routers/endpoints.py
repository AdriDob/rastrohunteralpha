from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.schemas.models import EndpointOut, PaginatedResponse
from api.services.data_service import create_endpoint as svc_create_endpoint
from api.services.data_service import get_endpoint, list_endpoints

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])


class EndpointCreate(BaseModel):
    target_id: int
    path: str
    method: str = "GET"
    params: dict[str, Any] | None = None


class EndpointAnalysisRequest(BaseModel):
    path: str
    method: str = "GET"
    params: dict[str, Any] | None = None
    model: str | None = None


@router.post("")
def create_endpoint(body: EndpointCreate):
    try:
        return svc_create_endpoint(
            target_id=body.target_id,
            path=body.path,
            method=body.method,
            params=body.params,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/analyze")
def analyze_endpoint(body: EndpointAnalysisRequest):
    from core_engines.engine.unified_classifier import classify as unified_classify
    result = {"local": unified_classify(body.path, body.method, body.params or {})}
    try:
        from core_engines.ai.analyzer import AIAnalyzer
        ai = AIAnalyzer()
        result["ai"] = ai.analyze_endpoint(body.path, body.method, body.params or {})
    except Exception as exc:
        result["ai_error"] = str(exc)
    return result


@router.get("", response_model=PaginatedResponse)
def get_endpoints(
    target_id: int | None = Query(None, description="Filter by target ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("path"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_endpoints(target_id=target_id, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{endpoint_id}", response_model=EndpointOut)
def get_endpoint_detail(endpoint_id: int):
    ep = get_endpoint(endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return ep
