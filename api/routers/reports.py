from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas.models import ReportFullOut, ReportListItem, ReportOut
from api.services.data_service import generate_report
from core_engines.pipeline.report_service import get_report, list_reports

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/generate", response_model=ReportOut)
def get_aggregate_report():
    return generate_report()


@router.get("", response_model=dict)
def get_reports_list(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    from database import db
    session = db.SessionLocal()
    try:
        items, total = list_reports(session, limit=limit, offset=offset)
        return {"items": items, "total": total}
    finally:
        session.close()


@router.get("/{report_id}", response_model=ReportFullOut)
def get_single_report(report_id: int):
    from database import db
    session = db.SessionLocal()
    try:
        report = get_report(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return ReportFullOut(**report)
    finally:
        session.close()
