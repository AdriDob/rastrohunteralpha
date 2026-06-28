from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


class InvestigationCreateBody(BaseModel):
    target_id: int
    name: str
    notes: str | None = None
    tags: list[str] | None = None


class InvestigationUpdateBody(BaseModel):
    name: str | None = None
    status: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    pipeline_state: dict[str, Any] | None = None


@router.post("")
def create_investigation(body: InvestigationCreateBody):
    from database import db, models

    session = db.SessionLocal()
    try:
        target = session.query(models.Target).filter(models.Target.id == body.target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")

        existing = (
            session.query(models.Investigation)
            .filter(
                models.Investigation.target_id == body.target_id,
                models.Investigation.name == body.name,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Investigation with this name already exists for this target")

        inv = models.Investigation(
            target_id=body.target_id,
            name=body.name,
            status="active",
            notes=body.notes,
            tags=json.dumps(body.tags or []),
            pipeline_state=json.dumps({}),
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)

        return _serialize(inv)
    finally:
        session.close()


@router.get("")
def list_investigations(
    target_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    from database import db, models

    session = db.SessionLocal()
    try:
        q = session.query(models.Investigation)
        if target_id is not None:
            q = q.filter(models.Investigation.target_id == target_id)
        if status:
            q = q.filter(models.Investigation.status == status)
        total = q.count()
        rows = q.order_by(models.Investigation.updated_at.desc()).offset(offset).limit(limit).all()
        items = [_serialize(r) for r in rows]
        return {"items": items, "total": total}
    finally:
        session.close()


@router.get("/{investigation_id}")
def get_investigation(investigation_id: int):
    from database import db

    session = db.SessionLocal()
    try:
        inv = _get_or_404(session, investigation_id)
        return _serialize(inv)
    finally:
        session.close()


@router.put("/{investigation_id}")
def update_investigation(investigation_id: int, body: InvestigationUpdateBody):
    from database import db

    session = db.SessionLocal()
    try:
        inv = _get_or_404(session, investigation_id)

        if body.name is not None:
            inv.name = body.name
        if body.status is not None:
            inv.status = body.status
        if body.notes is not None:
            inv.notes = body.notes
        if body.tags is not None:
            inv.tags = json.dumps(body.tags)
        if body.pipeline_state is not None:
            existing = json.loads(inv.pipeline_state) if inv.pipeline_state else {}
            existing.update(body.pipeline_state)
            inv.pipeline_state = json.dumps(existing)

        session.commit()
        session.refresh(inv)
        return _serialize(inv)
    finally:
        session.close()


@router.delete("/{investigation_id}")
def delete_investigation(investigation_id: int):
    from database import db

    session = db.SessionLocal()
    try:
        inv = _get_or_404(session, investigation_id)
        session.delete(inv)
        session.commit()
        return {"deleted": True}
    finally:
        session.close()


@router.get("/{investigation_id}/dashboard")
def investigation_dashboard(investigation_id: int):
    from database import db, models

    session = db.SessionLocal()
    try:
        inv = _get_or_404(session, investigation_id)

        endpoint_count = session.query(models.Endpoint).filter(
            models.Endpoint.target_id == inv.target_id
        ).count()

        findings = (
            session.query(models.Finding)
            .filter(models.Finding.target_id == inv.target_id)
            .all()
        )
        finding_count = len(findings)
        by_severity: dict[str, int] = {}
        for f in findings:
            s = f.severity or "unknown"
            by_severity[s] = by_severity.get(s, 0) + 1

        verdicts = session.query(models.Verdict).filter(
            models.Verdict.endpoint_id.in_(
                session.query(models.Endpoint.id).filter(
                    models.Endpoint.target_id == inv.target_id
                )
            )
        ).all() if endpoint_count > 0 else []
        confirmed_count = sum(1 for v in verdicts if v.status == "confirmed")

        reports = (
            session.query(models.Report)
            .order_by(models.Report.created_at.desc())
            .limit(10)
            .all()
        )

        # ── Pipeline state tracking ────────────────────────────────
        pipeline_state = json.loads(inv.pipeline_state) if inv.pipeline_state else {}
        hypotheses_count = len(pipeline_state.get("hypotheses", []))
        validated_count = pipeline_state.get("validated_count", confirmed_count)
        total_stages = 5  # recon, hypotheses, validation, evidence, report

        stages_passed = 1  # target selected
        timeline = []
        if endpoint_count > 0:
            stages_passed += 1
            timeline.append({"stage": "recon", "status": "done", "label": f"{endpoint_count} endpoints discovered", "timestamp": inv.created_at.isoformat() if inv.created_at else None})
        if hypotheses_count > 0:
            stages_passed += 1
            timeline.append({"stage": "hypotheses", "status": "done", "label": f"{hypotheses_count} hypotheses generated", "timestamp": inv.updated_at.isoformat() if inv.updated_at else None})
        else:
            timeline.append({"stage": "hypotheses", "status": "pending", "label": "Awaiting hypotheses", "timestamp": None})
        if validated_count > 0:
            stages_passed += 1
            timeline.append({"stage": "validation", "status": "done", "label": f"{validated_count} findings validated", "timestamp": None})
        if confirmed_count > 0:
            stages_passed += 1
            timeline.append({"stage": "evidence", "status": "done", "label": f"{confirmed_count} confirmed verdicts", "timestamp": None})
        if len(reports) > 0:
            stages_passed += 1
            timeline.append({"stage": "report", "status": "done", "label": f"{len(reports)} reports generated", "timestamp": reports[0].created_at.isoformat() if reports[0].created_at else None})
        else:
            timeline.append({"stage": "report", "status": "pending", "label": "No reports yet", "timestamp": None})

        progress_pct = min(100, int((stages_passed / total_stages) * 100))
        overall_confidence = min(1.0, max(0.0, confirmed_count / max(finding_count, 1)))

        return {
            "investigation": _serialize(inv),
            "stats": {
                "endpoints": endpoint_count,
                "findings": finding_count,
                "findings_by_severity": by_severity,
                "verdicts": len(verdicts),
                "confirmed_verdicts": confirmed_count,
            },
            "pipeline": {
                "stages": {
                    "recon": endpoint_count,
                    "hypotheses": hypotheses_count,
                    "validation": validated_count,
                    "evidence": confirmed_count,
                    "reported": len(reports),
                },
                "timeline": timeline,
                "overall_confidence": round(overall_confidence, 2),
                "progress_pct": progress_pct,
            },
        }
    finally:
        session.close()


def _get_or_404(session, investigation_id: int):
    from database import models

    inv = session.query(models.Investigation).filter(models.Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


def _serialize(inv) -> dict[str, Any]:
    tags_list = json.loads(inv.tags) if inv.tags else []
    pipeline = json.loads(inv.pipeline_state) if inv.pipeline_state else {}
    return {
        "id": inv.id,
        "target_id": inv.target_id,
        "name": inv.name,
        "status": inv.status,
        "pipeline_state": pipeline,
        "notes": inv.notes,
        "tags": tags_list,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }
