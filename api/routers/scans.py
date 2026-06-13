from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.schemas.models import PaginatedResponse
from api.services.data_service import list_scan_runs, get_scan_run

router = APIRouter(prefix="/api/scans", tags=["scans"])


class ScanRequest(BaseModel):
    target_name: str
    target_domain: Optional[str] = None
    mode: str = "FAST"


@router.post("")
async def launch_scan(request: ScanRequest):
    from core.orchestrator.scan_service import launch_scan as service_launch_scan
    from database import db
    session = db.SessionLocal()
    try:
        result = await service_launch_scan(
            target_name=request.target_name,
            target_domain=request.target_domain,
            target_mode=request.mode,
            session=session,
        )
        return result
    finally:
        session.close()


@router.get("/runs")
def get_scan_runs(
    target_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    return list_scan_runs(target_id=target_id, limit=limit)


@router.get("/runs/{scan_id}")
def get_scan_run_detail(scan_id: int):
    run = get_scan_run(scan_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found")
    return run
