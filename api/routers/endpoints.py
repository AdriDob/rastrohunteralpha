from fastapi import APIRouter, HTTPException, Query

from api.schemas.models import EndpointOut, PaginatedResponse
from api.services.data_service import list_endpoints, get_endpoint

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])


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
