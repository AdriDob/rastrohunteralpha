from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.schemas.models import FindingOut, PaginatedResponse
from api.services.data_service import list_findings, create_finding as svc_create_finding

router = APIRouter(prefix="/api/findings", tags=["findings"])


class FindingCreate(BaseModel):
    target_id: int
    endpoint_id: Optional[int] = None
    title: str
    severity: Optional[str] = "medium"
    description: Optional[str] = None


@router.post("")
def create_finding(body: FindingCreate):
    try:
        return svc_create_finding(
            target_id=body.target_id,
            title=body.title,
            severity=body.severity or "medium",
            description=body.description,
            endpoint_id=body.endpoint_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=PaginatedResponse)
def get_findings(
    target_id: int | None = Query(None, description="Filter by target ID"),
    endpoint_id: int | None = Query(None, description="Filter by endpoint ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("severity"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_findings(target_id=target_id, endpoint_id=endpoint_id, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
    return {"items": items, "total": total, "skip": skip, "limit": limit}
