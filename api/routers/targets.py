from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.schemas.models import PaginatedResponse, TargetOut, TargetSummaryOut
from api.services.data_service import list_targets, get_target, create_target as svc_create_target

router = APIRouter(prefix="/api/targets", tags=["targets"])


class TargetCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    mode: Optional[str] = "FAST"


@router.post("")
def create_target(body: TargetCreate):
    return svc_create_target(name=body.name, domain=body.domain)


@router.get("", response_model=PaginatedResponse)
def get_targets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_targets(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{target_id}", response_model=TargetSummaryOut)
def get_target_detail(target_id: int):
    t = get_target(target_id)
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    return t


@router.get("/{target_id}/summary")
def get_target_summary(target_id: int):
    from database import db, models
    t = get_target(target_id)
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    from core_engines.engine.unified_classifier import classify as unified_classify
    from core_engines.engine.unified_scoring import score_target as unified_score_target
    session = db.SessionLocal()
    try:
        endpoints_raw = session.query(models.Endpoint).filter(models.Endpoint.target_id == target_id).all()
    finally:
        session.close()
    entries = []
    has_api = False
    multi_tenant = False
    has_admin = False
    has_graphql = False
    for ep in endpoints_raw:
        params = ep.parsed_params if hasattr(ep, 'parsed_params') else {}
        metadata = unified_classify(ep.path, ep.method, params)
        labels = metadata.get("labels", [])
        entries.append({"path": ep.path, "method": ep.method, "labels": labels})
        if not has_api and "api" in labels:
            has_api = True
        if not multi_tenant and ("org" in labels or "tenant" in labels):
            multi_tenant = True
        if not has_admin and "admin" in labels:
            has_admin = True
        if not has_graphql and "graphql" in labels:
            has_graphql = True
    sc = unified_score_target({
        "is_saas": bool(t.get("domain")),
        "has_api": has_api,
        "multi_tenant": multi_tenant,
        "has_admin": has_admin,
        "has_graphql": has_graphql,
    })
    return {"target": t, "endpoints": entries, "score": sc}
