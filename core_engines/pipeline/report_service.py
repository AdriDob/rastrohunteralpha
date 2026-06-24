from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

from core_engines.intelligence.reward_learning import RewardLearner
from core_engines.pipeline.stages import PipelineContext, PipelineStage
from core_engines.validation.gate import Verdict
from database import models

logger = logging.getLogger("rastro.pipeline.report_service")

REPORT_STATUSES = [
    "draft", "ready", "submitted", "need_more_info",
    "triaged", "resolved", "paid", "duplicate", "informative", "na",
]


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
        severity=report_dict.get("severity", "medium"),
        status="draft",
    )
    session.add(db_report)
    session.commit()
    session.refresh(db_report)

    ctx.report_id = db_report.id
    ctx.stage = PipelineStage.REPORT_GENERATED
    ctx.metadata["report_summary"] = report_dict.get("summary", "")
    logger.info("Report %d saved for verdict %s", db_report.id, verdict.hot_path_id)
    return ctx


def _report_to_dict(r: models.Report) -> Dict[str, Any]:
    content = json.loads(r.content) if r.content else {}
    return {
        "id": r.id,
        "investigation_id": r.investigation_id,
        "format": r.format,
        "content": content,
        "finding_ids": json.loads(r.finding_ids) if r.finding_ids else [],
        "program": r.program or "",
        "target": r.target or "",
        "vulnerability": r.vulnerability or "",
        "severity": r.severity or "medium",
        "status": r.status or "draft",
        "estimated_reward": r.estimated_reward or 0.0,
        "confirmed_reward": r.confirmed_reward or 0.0,
        "currency": r.currency or "USD",
        "evidence_count": r.evidence_count or 0,
        "notes": r.notes or "",
        "timeline": json.loads(r.timeline) if r.timeline else [],
        "attachments": json.loads(r.attachments) if r.attachments else [],
        "summary": content.get("summary", "") if isinstance(content, dict) else "",
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def create_report_from_findings(
    session: Session,
    finding_ids: List[int],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    findings = session.query(models.Finding).filter(models.Finding.id.in_(finding_ids)).all()
    if not findings:
        raise ValueError("No findings found for the given IDs")

    target_ids = {f.target_id for f in findings}
    targets = {
        t.id: t
        for t in session.query(models.Target).filter(models.Target.id.in_(target_ids)).all()
    }

    severities = [f.severity or "medium" for f in findings]
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    worst = min(severities, key=lambda s: severity_order.get(s, 99))

    target_names = [targets[f.target_id].name for f in findings if f.target_id in targets]
    target_str = ", ".join(sorted(set(target_names)))

    title_str = "; ".join(f.title for f in findings[:3])
    if len(findings) > 3:
        title_str += f" (+{len(findings) - 3} more)"

    extra = extra or {}
    content_dict = {
        "summary": extra.get("summary", title_str),
        "findings": [
            {
                "id": f.id,
                "title": f.title,
                "severity": f.severity or "medium",
                "description": f.description or "",
                "target": targets[f.target_id].name if f.target_id in targets else "",
            }
            for f in findings
        ],
        "total_findings": len(findings),
    }

    db_report = models.Report(
        investigation_id=None,
        format="markdown",
        content=json.dumps(content_dict, ensure_ascii=False),
        finding_ids=json.dumps(finding_ids),
        program=extra.get("program", ""),
        target=extra.get("target", target_str),
        vulnerability=extra.get("vulnerability", title_str),
        severity=extra.get("severity", worst),
        status="draft",
        notes=extra.get("notes", ""),
    )
    session.add(db_report)
    session.commit()
    session.refresh(db_report)

    logger.info("Report %d created from %d finding(s)", db_report.id, len(findings))
    return _report_to_dict(db_report)


def get_report(session: Session, report_id: int) -> Optional[Dict[str, Any]]:
    db_report = session.query(models.Report).filter(models.Report.id == report_id).first()
    if not db_report:
        return None
    return _report_to_dict(db_report)


def list_reports(
    session: Session,
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], int]:
    query = session.query(models.Report)

    if status_filter and status_filter != "all":
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.filter(models.Report.status.in_(statuses))

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            models.Report.program.ilike(pattern)
            | models.Report.target.ilike(pattern)
            | models.Report.vulnerability.ilike(pattern)
        )

    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.filter(models.Report.created_at >= dt)
        except (ValueError, TypeError):
            pass

    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(models.Report.created_at <= dt)
        except (ValueError, TypeError):
            pass

    total = query.count()

    order_col = getattr(models.Report, sort_by, models.Report.created_at)
    order_fn = desc if sort_order == "desc" else asc
    rows = (
        query
        .order_by(order_fn(order_col))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [_report_to_dict(r) for r in rows]
    return items, total


def update_report(
    session: Session,
    report_id: int,
    updates: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    db_report = session.query(models.Report).filter(models.Report.id == report_id).first()
    if not db_report:
        return None

    simple_fields = {
        "program", "target", "vulnerability", "severity", "status",
        "format", "estimated_reward", "confirmed_reward", "currency",
        "evidence_count", "notes",
    }
    json_fields = {"timeline", "attachments"}

    for key, value in updates.items():
        if key in simple_fields:
            setattr(db_report, key, value)
        elif key in json_fields and isinstance(value, (list, dict)):
            setattr(db_report, key, json.dumps(value, ensure_ascii=False))

    db_report.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(db_report)

    logger.info("Report %d updated: %s", report_id, updates)

    # Feed confirmed_reward updates into RewardLearner for continuous learning
    if "confirmed_reward" in updates or "status" in updates:
        try:
            learner = RewardLearner()
            learner.analyze()
            adjustments = learner.get_adjustments()
            if adjustments:
                logger.debug("RewardLearner adjustments updated after report %d", report_id)
        except Exception as exc:
            logger.debug("RewardLearner update failed (non-fatal): %s", exc)

    return _report_to_dict(db_report)


def report_stats(session: Session) -> Dict[str, Any]:
    total = session.query(models.Report).count()
    status_counts: Dict[str, int] = {}
    for s in REPORT_STATUSES:
        status_counts[s] = session.query(models.Report).filter(models.Report.status == s).count()

    paid_reports = session.query(models.Report).filter(models.Report.status == "paid").all()
    total_rewards = sum(r.confirmed_reward or 0 for r in paid_reports)
    estimated_rewards = sum(r.estimated_reward or 0 for r in session.query(models.Report).all())

    paid_count = status_counts.get("paid", 0)

    return {
        "total": total,
        "status_counts": status_counts,
        "paid_count": paid_count,
        "total_rewards": total_rewards,
        "estimated_rewards": estimated_rewards,
    }
