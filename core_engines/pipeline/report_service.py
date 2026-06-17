from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core_engines.pipeline.stages import PipelineContext, PipelineStage
from core_engines.validation.gate import Verdict
from database import models

logger = logging.getLogger("rastro.pipeline.report_service")


def generate_and_save_report(
    session: Session,
    ctx: PipelineContext,
    verdict: Verdict,
    endpoint: Any,
    findings_data: Optional[Dict[str, Any]] = None,
) -> PipelineContext:
    from core_engines.reporting.reporting import ReportGenerator

    if verdict.status != "confirmed" or verdict.confidence < 0.6:
        ctx.stage = PipelineStage.FAILED
        ctx.metadata["report_skip_reason"] = "verdict not confirmed or confidence below 0.6"
        return ctx

    generator = ReportGenerator()
    report_dict = generator.draft_report(
        findings=findings_data or {},
        verdict=verdict,
        evidence_list=ctx.metadata.get("evidence_records"),
    )

    content = json.dumps(report_dict, ensure_ascii=False)
    finding_ids = json.dumps([ctx.finding_id] if ctx.finding_id else [])

    db_report = models.Report(
        investigation_id=None,
        format="markdown",
        content=content,
        finding_ids=finding_ids,
    )
    session.add(db_report)
    session.commit()
    session.refresh(db_report)

    ctx.report_id = db_report.id
    ctx.stage = PipelineStage.REPORT_GENERATED
    ctx.metadata["report_summary"] = report_dict.get("summary", "")
    logger.info("Report %d saved for verdict %s", db_report.id, verdict.hot_path_id)
    return ctx


def get_report(session: Session, report_id: int) -> Optional[Dict[str, Any]]:
    db_report = session.query(models.Report).filter(models.Report.id == report_id).first()
    if not db_report:
        return None
    return {
        "id": db_report.id,
        "investigation_id": db_report.investigation_id,
        "format": db_report.format,
        "content": json.loads(db_report.content) if db_report.content else None,
        "finding_ids": json.loads(db_report.finding_ids) if db_report.finding_ids else [],
        "created_at": db_report.created_at.isoformat() if db_report.created_at else None,
    }


def list_reports(
    session: Session,
    limit: int = 20,
    offset: int = 0,
) -> tuple[List[Dict[str, Any]], int]:
    total = session.query(models.Report).count()
    rows = (
        session.query(models.Report)
        .order_by(models.Report.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = []
    for r in rows:
        content = json.loads(r.content) if r.content else {}
        items.append({
            "id": r.id,
            "format": r.format,
            "summary": content.get("summary", "") if isinstance(content, dict) else "",
            "severity": content.get("severity", "") if isinstance(content, dict) else "",
            "finding_ids": json.loads(r.finding_ids) if r.finding_ids else [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return items, total
