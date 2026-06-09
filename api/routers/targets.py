from fastapi import APIRouter, HTTPException, Query

from api.schemas.models import PaginatedResponse, TargetOut, TargetSummaryOut
from api.services.data_service import list_targets, get_target

router = APIRouter(prefix="/api/targets", tags=["targets"])


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
