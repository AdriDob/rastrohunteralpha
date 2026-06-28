
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response

from api.schemas.models import ReportCreate, ReportFullOut, ReportOut, ReportUpdate
from api.services.data_service import generate_report
from core_engines.export.service import export_report, get_report_versions, save_report_version
from core_engines.intelligence.reward_learning import RewardLearner
from core_engines.pipeline.report_service import (
    create_report_from_findings,
    get_report,
    list_reports,
    report_stats,
    update_report,
)
from core_engines.tracking.service import get_submission_status, submit_report_to_platform

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/generate", response_model=ReportOut)
def get_aggregate_report():
    return generate_report()


@router.get("/stats")
def get_report_statistics():
    from database import db

    session = db.SessionLocal()
    try:
        stats = report_stats(session)
        return stats
    finally:
        session.close()


@router.post("", response_model=ReportFullOut)
def create_new_report(body: ReportCreate):
    from database import db

    session = db.SessionLocal()
    try:
        report = create_report_from_findings(
            session,
            finding_ids=body.finding_ids,
            extra=body.model_dump(exclude={"finding_ids"}, exclude_none=True),
        )
        return ReportFullOut(**report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        session.close()


@router.get("", response_model=dict)
def get_reports_list(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="Filter by status(es), comma-separated"),
    search: str | None = Query(None, description="Search program, target, vulnerability"),
    sort_by: str = Query("created_at", description="Sort column"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    date_from: str | None = Query(None, description="ISO date filter start"),
    date_to: str | None = Query(None, description="ISO date filter end"),
):
    from database import db

    session = db.SessionLocal()
    try:
        items, total = list_reports(
            session,
            limit=limit,
            offset=offset,
            status_filter=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            date_from=date_from,
            date_to=date_to,
        )
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


@router.put("/{report_id}", response_model=ReportFullOut)
def update_single_report(report_id: int, body: ReportUpdate):
    from database import db

    session = db.SessionLocal()
    try:
        updates = body.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        report = update_report(session, report_id, updates)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return ReportFullOut(**report)
    finally:
        session.close()


@router.get("/{report_id}/export")
def export_single_report(report_id: int, format: str = Query("markdown", pattern="^(markdown|html|pdf|txt)$")):
    try:
        content, mime = export_report(report_id, format)
        if isinstance(content, bytes):
            return Response(content=content, media_type=mime, headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.{format}"',
            })
        if mime == "text/markdown":
            return PlainTextResponse(content=content, media_type=mime, headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.md"',
            })
        return PlainTextResponse(content=content, media_type=mime)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{report_id}/versions")
def list_report_versions(report_id: int):
    from database import db
    session = db.SessionLocal()
    try:
        report = get_report(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        versions = get_report_versions(report_id)
        return {"versions": versions, "total": len(versions)}
    finally:
        session.close()


@router.post("/{report_id}/versions")
def create_report_version(report_id: int, body: dict[str, str] = None):
    from database import db
    if body is None:
        body = {}
    session = db.SessionLocal()
    try:
        report = get_report(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        version = save_report_version(report_id, summary=body.get("summary", ""))
        return {**version, "status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        session.close()


@router.post("/{report_id}/submit")
def submit_report_to_platform_endpoint(report_id: int, body: dict[str, str]):
    platform = body.get("platform", "")
    if not platform:
        raise HTTPException(status_code=400, detail="platform is required")
    result = submit_report_to_platform(report_id, platform)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Submission failed"))
    return result


@router.get("/{report_id}/submissions")
def get_report_submissions(report_id: int):
    from database import db
    session = db.SessionLocal()
    try:
        report = get_report(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        submissions = get_submission_status(report_id)
        return {"submissions": submissions, "total": len(submissions)}
    finally:
        session.close()


@router.get("/reward-learning")
def get_reward_learning():
    """Run reward learning analysis on all reports and return results."""
    learner = RewardLearner()
    result = learner.analyze()
    return {
        "generated_at": result.generated_at,
        "total_reports": result.total_reports,
        "total_confirmed": result.total_confirmed,
        "total_confirmed_value": result.total_confirmed_value,
        "overall_acceptance_rate": result.overall_acceptance_rate,
        "by_type": {
            vt: {
                "vulnerability_type": s.vulnerability_type,
                "count": s.count,
                "confirmed_count": s.confirmed_count,
                "total_estimated": s.total_estimated,
                "total_confirmed": s.total_confirmed,
                "avg_estimated": s.avg_estimated,
                "avg_confirmed": s.avg_confirmed,
                "base_payout": s.base_payout,
                "learned_payout": s.learned_payout,
                "adjustment_factor": s.adjustment_factor,
            }
            for vt, s in result.by_type.items()
        },
        "by_program": {
            prog: {
                "program": m.program,
                "report_count": m.report_count,
                "confirmed_count": m.confirmed_count,
                "acceptance_rate": m.acceptance_rate,
                "total_confirmed": m.total_confirmed,
                "avg_payout": m.avg_payout,
                "highest_payout": m.highest_payout,
                "avg_response_days": m.avg_response_days,
            }
            for prog, m in result.by_program.items()
        },
        "top_programs_by_payout": result.top_programs_by_payout,
        "top_programs_by_acceptance": result.top_programs_by_acceptance,
        "prediction_accuracy": result.prediction_accuracy,
        "summary": result.summary,
    }
