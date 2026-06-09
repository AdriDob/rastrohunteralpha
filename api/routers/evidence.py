from fastapi import APIRouter, HTTPException, Query

from api.schemas.models import EvidenceOut, PaginatedResponse
from api.services.data_service import list_evidence

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("", response_model=PaginatedResponse)
def get_evidence(
    verdict_id: int | None = Query(None, description="Filter by verdict ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("id"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_evidence(verdict_id=verdict_id, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
    return {"items": items, "total": total, "skip": skip, "limit": limit}
