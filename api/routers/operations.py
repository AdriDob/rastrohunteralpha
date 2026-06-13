"""
Rastro 2.5 Operations Layer — workflow, briefings, tasks, sessions, notifications.

All endpoints are read-only or metadata-only. Never modifies core pipeline data.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import db, models

logger = logging.getLogger("rastro.operations")

router = APIRouter(prefix="/api/operations", tags=["operations"])

TASK_STATUSES = ("pending", "in_progress", "waiting", "completed")

# ─── Block 1 & 2: Morning Brief / Evening Summary ───────────────────

def _build_morning_brief() -> Dict[str, Any]:
    session = db.SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)

        new_targets = session.query(models.Target).filter(models.Target.created_at >= since).count()
        new_endpoints = session.query(models.Endpoint).filter(models.Endpoint.discovered_at >= since).count()
        new_evidence = session.query(models.Evidence).filter(models.Evidence.created_at >= since).count()

        top_targets = session.query(models.Target).order_by(models.Target.created_at.desc()).limit(5).all()
        top_roi_target = None
        if top_targets:
            from core_engines.engine.unified_scoring import score_target as unified_score_target
            scored = []
            for t in top_targets:
                ep_count = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).count()
                roi = unified_score_target({
                    "api_count": ep_count, "source": (t.name or "").lower(),
                    "has_graphql": False, "has_admin": False, "has_api": False, "has_exports": False,
                })
                scored.append((t, roi.get("roi_score", 0)))
            scored.sort(key=lambda x: x[1], reverse=True)
            if scored:
                top_roi_target = {"id": scored[0][0].id, "name": scored[0][0].name, "roi": scored[0][1]}

        pending_reports = session.query(models.Finding).count()
        quick_wins_count = 0
        try:
            from core_engines.quick_wins.quick_wins_engine import QuickWinsEngine
            from core_engines.engine.snapshot import PipelineSnapshot
            engine = QuickWinsEngine()
            report = engine.evaluate(PipelineSnapshot(status="completed", target=None, endpoints=[], hot_paths=[], verdicts=[], reports=[], coverage_score=0.0, timestamp=now.isoformat()))
            quick_wins_count = report.total_opportunities
        except Exception:
            pass

        return {
            "generated_at": now.isoformat(),
            "period": "24h",
            "new_targets": new_targets,
            "new_endpoints": new_endpoints,
            "new_evidence": new_evidence,
            "quick_wins_count": quick_wins_count,
            "pending_findings": pending_reports,
            "highest_roi_opportunity": top_roi_target,
            "summary": f"{new_targets} new targets, {new_endpoints} new endpoints, {new_evidence} new evidence records in the last 24h",
        }
    finally:
        session.close()


def _build_evening_summary() -> Dict[str, Any]:
    session = db.SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)

        scans = session.query(models.ScanRun).filter(models.ScanRun.started_at >= since).count()
        endpoints = session.query(models.Endpoint).filter(models.Endpoint.discovered_at >= since).count()
        evidence = session.query(models.Evidence).filter(models.Evidence.created_at >= since).count()
        verdicts = session.query(models.Verdict).filter(models.Verdict.created_at >= since).count()
        findings = session.query(models.Finding).filter(models.Finding.created_at >= since).count()

        memory_records = session.query(models.MemoryRecord).filter(models.MemoryRecord.created_at >= since).count()

        return {
            "generated_at": now.isoformat(),
            "period": "24h",
            "scans_executed": scans,
            "endpoints_discovered": endpoints,
            "evidence_generated": evidence,
            "verdicts_created": verdicts,
            "reports_produced": findings,
            "adaptive_learning_updates": memory_records,
            "total_events": scans + endpoints + evidence + verdicts + findings + memory_records,
            "summary": f"{scans} scans, {endpoints} endpoints, {evidence} evidence, {verdicts} verdicts, {findings} findings today",
        }
    finally:
        session.close()


@router.get("/briefing/morning")
def morning_brief():
    return _build_morning_brief()


@router.get("/briefing/evening")
def evening_summary():
    return _build_evening_summary()


# ─── Block 3: Unified Activity Timeline ─────────────────────────────

@router.get("/timeline")
def unified_timeline(
    limit: int = Query(50, ge=1, le=200),
    hours: int = Query(72, ge=1, le=720),
    event_type: Optional[str] = Query(None),
):
    session = db.SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        events: List[Dict[str, Any]] = []

        for f in session.query(models.Finding).filter(models.Finding.created_at >= since).all():
            events.append({
                "type": "finding", "id": f.id, "label": f.title or f"Finding #{f.id}",
                "severity": f.severity or "medium", "target_id": f.target_id,
                "timestamp": f.created_at.isoformat() if f.created_at else "",
            })

        for v in session.query(models.Verdict).filter(models.Verdict.created_at >= since).all():
            events.append({
                "type": "verdict", "id": v.id, "label": f"Verdict #{v.id}",
                "status": v.status, "confidence": float(v.confidence) if v.confidence else 0.0,
                "timestamp": v.created_at.isoformat() if v.created_at else "",
            })

        for s in session.query(models.ScanRun).filter(models.ScanRun.started_at >= since).all():
            events.append({
                "type": "scan", "id": s.id, "label": f"Scan #{s.id}",
                "status": s.status, "mode": s.mode, "endpoint_count": s.endpoint_count,
                "target_id": s.target_id,
                "timestamp": s.started_at.isoformat() if s.started_at else "",
            })

        for e in session.query(models.Evidence).filter(models.Evidence.created_at >= since).all():
            events.append({
                "type": "evidence", "id": e.id, "label": f"Evidence #{e.id}",
                "attempt": e.attempt_label, "url": e.request_url,
                "timestamp": e.created_at.isoformat() if e.created_at else "",
            })

        for mr in session.query(models.MemoryRecord).filter(models.MemoryRecord.created_at >= since).all():
            events.append({
                "type": "intelligence", "id": mr.id, "label": mr.key or "Memory record",
                "category": mr.category,
                "timestamp": mr.created_at.isoformat() if mr.created_at else "",
            })

        for n in session.query(models.Notification).filter(models.Notification.created_at >= since).all():
            events.append({
                "type": "notification", "id": n.id, "label": n.message,
                "notification_type": n.notification_type,
                "timestamp": n.created_at.isoformat() if n.created_at else "",
            })

        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        if event_type:
            events = [e for e in events if e["type"] == event_type]

        return {"events": events[:limit], "total": len(events), "since": since.isoformat()}
    finally:
        session.close()


# ─── Block 4: Workspace Favorites ───────────────────────────────────

class FavoriteCreate(BaseModel):
    item_type: str
    item_id: int
    label: Optional[str] = None


@router.get("/favorites")
def list_favorites(item_type: Optional[str] = Query(None)):
    session = db.SessionLocal()
    try:
        q = session.query(models.Favorite)
        if item_type:
            q = q.filter(models.Favorite.item_type == item_type)
        items = q.order_by(models.Favorite.created_at.desc()).limit(100).all()
        return {"items": [{"id": f.id, "item_type": f.item_type, "item_id": f.item_id,
                           "label": f.label, "created_at": f.created_at.isoformat() if f.created_at else ""} for f in items]}
    finally:
        session.close()


@router.post("/favorites")
def add_favorite(body: FavoriteCreate):
    session = db.SessionLocal()
    try:
        existing = session.query(models.Favorite).filter(
            models.Favorite.item_type == body.item_type,
            models.Favorite.item_id == body.item_id,
        ).first()
        if existing:
            return {"id": existing.id, "status": "already_exists"}
        fav = models.Favorite(item_type=body.item_type, item_id=body.item_id, label=body.label)
        session.add(fav)
        session.commit()
        return {"id": fav.id, "status": "created"}
    finally:
        session.close()


@router.delete("/favorites/{favorite_id}")
def remove_favorite(favorite_id: int):
    session = db.SessionLocal()
    try:
        fav = session.query(models.Favorite).filter(models.Favorite.id == favorite_id).first()
        if not fav:
            raise HTTPException(status_code=404, detail="Favorite not found")
        session.delete(fav)
        session.commit()
        return {"status": "deleted"}
    finally:
        session.close()


# ─── Block 5: Task Queue ────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    linked_type: Optional[str] = None
    linked_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


@router.get("/tasks")
def list_tasks(status: Optional[str] = Query(None), priority: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    session = db.SessionLocal()
    try:
        q = session.query(models.Task)
        if status:
            q = q.filter(models.Task.status == status)
        if priority:
            q = q.filter(models.Task.priority == priority)
        items = q.order_by(models.Task.updated_at.desc()).limit(limit).all()
        return {"items": [{"id": t.id, "title": t.title, "description": t.description,
                           "status": t.status, "priority": t.priority,
                           "linked_type": t.linked_type, "linked_id": t.linked_id,
                           "created_at": t.created_at.isoformat() if t.created_at else "",
                           "updated_at": t.updated_at.isoformat() if t.updated_at else ""} for t in items]}
    finally:
        session.close()


@router.post("/tasks")
def create_task(body: TaskCreate):
    if body.status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {TASK_STATUSES}")
    session = db.SessionLocal()
    try:
        task = models.Task(title=body.title, description=body.description,
                           status=body.status, priority=body.priority,
                           linked_type=body.linked_type, linked_id=body.linked_id)
        session.add(task)
        session.commit()
        return {"id": task.id, "status": "created"}
    finally:
        session.close()


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate):
    session = db.SessionLocal()
    try:
        task = session.query(models.Task).filter(models.Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if body.title is not None:
            task.title = body.title
        if body.description is not None:
            task.description = body.description
        if body.status is not None:
            if body.status not in TASK_STATUSES:
                raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {TASK_STATUSES}")
            task.status = body.status
        if body.priority is not None:
            task.priority = body.priority
        session.commit()
        return {"id": task.id, "status": "updated"}
    finally:
        session.close()


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    session = db.SessionLocal()
    try:
        task = session.query(models.Task).filter(models.Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        session.delete(task)
        session.commit()
        return {"status": "deleted"}
    finally:
        session.close()


# ─── Block 6: Session Manager ──────────────────────────────────────

class SessionUpdate(BaseModel):
    name: Optional[str] = None
    current_target_id: Optional[int] = None
    current_investigation: Optional[Dict[str, Any]] = None
    open_evidence_ids: Optional[List[int]] = None
    current_replay_id: Optional[int] = None
    current_report_draft: Optional[Dict[str, Any]] = None


@router.get("/session")
def get_session():
    session = db.SessionLocal()
    try:
        s = session.query(models.Session).order_by(models.Session.updated_at.desc()).first()
        if not s:
            return {"id": None, "name": "No active session"}
        return {
            "id": s.id, "name": s.name,
            "current_target_id": s.current_target_id,
            "current_investigation": json.loads(s.current_investigation) if s.current_investigation else None,
            "open_evidence_ids": json.loads(s.open_evidence_ids) if s.open_evidence_ids else [],
            "current_replay_id": s.current_replay_id,
            "current_report_draft": json.loads(s.current_report_draft) if s.current_report_draft else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else "",
        }
    finally:
        session.close()


@router.put("/session")
def update_session(body: SessionUpdate):
    db_session = db.SessionLocal()
    try:
        s = db_session.query(models.Session).order_by(models.Session.updated_at.desc()).first()
        if not s:
            s = models.Session(name="Default Session")
            db_session.add(s)
        if body.name is not None:
            s.name = body.name
        if body.current_target_id is not None:
            s.current_target_id = body.current_target_id
        if body.current_investigation is not None:
            s.current_investigation = json.dumps(body.current_investigation)
        if body.open_evidence_ids is not None:
            s.open_evidence_ids = json.dumps(body.open_evidence_ids)
        if body.current_replay_id is not None:
            s.current_replay_id = body.current_replay_id
        if body.current_report_draft is not None:
            s.current_report_draft = json.dumps(body.current_report_draft)
        db_session.commit()
        return {"id": s.id, "status": "updated"}
    finally:
        db_session.close()


# ─── Block 7: Operational Metrics ───────────────────────────────────

@router.get("/metrics")
def operational_metrics():
    session = db.SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        total_verdicts = session.query(models.Verdict).count()
        confirmed_verdicts = session.query(models.Verdict).filter(models.Verdict.status == "confirmed").count()
        total_findings = session.query(models.Finding).count()
        total_evidence = session.query(models.Evidence).count()
        evidence_this_week = session.query(models.Evidence).filter(models.Evidence.created_at >= week_ago).count()
        findings_this_week = session.query(models.Finding).filter(models.Finding.created_at >= week_ago).count()

        avg_time = 0.0
        avg_report_time = 0.0
        try:
            from core_engines.confidence import audit_verdicts
            conf_report = audit_verdicts(limit=200)

            confidence_dist = {
                "high": sum(1 for a in conf_report.audits if a.overall_score >= 0.7),
                "medium": sum(1 for a in conf_report.audits if a.overall_score >= 0.4 and a.overall_score < 0.7),
                "low": sum(1 for a in conf_report.audits if a.overall_score < 0.4),
            }
        except Exception:
            confidence_dist = {"high": 0, "medium": 0, "low": 0}

        return {
            "generated_at": now.isoformat(),
            "total_verdicts": total_verdicts,
            "confirmed_verdicts": confirmed_verdicts,
            "total_findings": total_findings,
            "total_evidence": total_evidence,
            "evidence_growth_7d": evidence_this_week,
            "findings_growth_7d": findings_this_week,
            "confidence_distribution": confidence_dist,
            "average_investigation_time_minutes": round(avg_time, 1),
            "average_report_creation_time_minutes": round(avg_report_time, 1),
            "quick_win_conversion_rate": round(confirmed_verdicts / max(total_verdicts, 1) * 100, 1),
        }
    finally:
        session.close()


# ─── Block 8: System Self Test ──────────────────────────────────────

@router.post("/self-test")
def system_self_test():
    results: List[Dict[str, Any]] = []
    all_ok = True

    try:
        db.init_db()
        session = db.SessionLocal()
        session.execute(db.text("SELECT 1"))
        session.close()
        results.append({"component": "database", "status": "ok", "detail": "Connection verified"})
    except Exception as e:
        all_ok = False
        results.append({"component": "database", "status": "error", "detail": str(e)})

    try:
        from api.main import app
        results.append({"component": "api", "status": "ok", "detail": f"App loaded, {len(app.routes)} routes"})
    except Exception as e:
        all_ok = False
        results.append({"component": "api", "status": "error", "detail": str(e)})

    try:
        from core_engines.engine.unified_scoring import score
        results.append({"component": "pipeline_scoring", "status": "ok", "detail": "Unified scoring loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "pipeline_scoring", "status": "error", "detail": str(e)})

    try:
        from core_engines.evidence.store import EvidenceStore
        results.append({"component": "evidence", "status": "ok", "detail": "Evidence store loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "evidence", "status": "error", "detail": str(e)})

    try:
        from core_engines.validation.verdict_handler import VerdictHandler
        results.append({"component": "verdicts", "status": "ok", "detail": "Verdict handler loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "verdicts", "status": "error", "detail": str(e)})

    try:
        from core_engines.reporting.reporting import ReportGenerator
        results.append({"component": "reports", "status": "ok", "detail": "Report generator loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "reports", "status": "error", "detail": str(e)})

    try:
        from core_engines.ai.assistant import get_assistant
        assistant = get_assistant()
        results.append({"component": "ai_assistant", "status": "ok", "detail": "AI Assistant loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "ai_assistant", "status": "error", "detail": str(e)})

    try:
        from core_engines.quick_wins.quick_wins_engine import QuickWinsEngine
        results.append({"component": "quick_wins", "status": "ok", "detail": "Quick Wins engine loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "quick_wins", "status": "error", "detail": str(e)})

    try:
        from core_engines.replay import build_replay
        results.append({"component": "replay", "status": "ok", "detail": "Replay engine loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "replay", "status": "error", "detail": str(e)})

    try:
        from core_engines.screenshot.engine import ScreenshotEngine
        results.append({"component": "screenshot", "status": "ok", "detail": "Screenshot engine loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "screenshot", "status": "error", "detail": str(e)})

    try:
        from core_engines.intelligence.adaptive_memory import get_memory
        memory = get_memory()
        results.append({"component": "adaptive_intelligence", "status": "ok", "detail": "Adaptive intelligence loaded"})
    except Exception as e:
        all_ok = False
        results.append({"component": "adaptive_intelligence", "status": "error", "detail": str(e)})

    try:
        from core_engines.timeline import build_timeline
        tl = build_timeline(limit=1)
        results.append({"component": "timeline", "status": "ok", "detail": f"Timeline built ({tl.total_events} events)"})
    except Exception as e:
        all_ok = False
        results.append({"component": "timeline", "status": "error", "detail": str(e)})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy" if all_ok else "degraded",
        "all_ok": all_ok,
        "components": results,
        "summary": f"{sum(1 for r in results if r['status'] == 'ok')}/{len(results)} components healthy",
    }


# ─── Block 9: Operational Notifications ─────────────────────────────

class NotificationCreate(BaseModel):
    notification_type: str
    message: str
    linked_type: Optional[str] = None
    linked_id: Optional[int] = None


@router.get("/notifications")
def list_notifications(unread_only: bool = Query(False), limit: int = Query(50, ge=1, le=100)):
    session = db.SessionLocal()
    try:
        q = session.query(models.Notification)
        if unread_only:
            q = q.filter(models.Notification.is_read == "false")
        items = q.order_by(models.Notification.created_at.desc()).limit(limit).all()
        return {"items": [{"id": n.id, "type": n.notification_type, "message": n.message,
                           "linked_type": n.linked_type, "linked_id": n.linked_id,
                           "is_read": n.is_read == "true",
                           "created_at": n.created_at.isoformat() if n.created_at else ""} for n in items]}
    finally:
        session.close()


@router.post("/notifications")
def create_notification(body: NotificationCreate):
    session = db.SessionLocal()
    try:
        n = models.Notification(notification_type=body.notification_type, message=body.message,
                                linked_type=body.linked_type, linked_id=body.linked_id)
        session.add(n)
        session.commit()
        return {"id": n.id, "status": "created"}
    finally:
        session.close()


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int):
    session = db.SessionLocal()
    try:
        n = session.query(models.Notification).filter(models.Notification.id == notification_id).first()
        if not n:
            raise HTTPException(status_code=404, detail="Notification not found")
        n.is_read = "true"
        session.commit()
        return {"status": "read"}
    finally:
        session.close()


@router.post("/notifications/mark-all-read")
def mark_all_notifications_read():
    session = db.SessionLocal()
    try:
        session.query(models.Notification).filter(models.Notification.is_read == "false").update({"is_read": "true"})
        session.commit()
        return {"status": "all_marked_read"}
    finally:
        session.close()


# ─── Block 9b: Auto-notification generator ──────────────────────────

_last_notification_check: Optional[datetime] = None


def _generate_notifications() -> int:
    """Check for new pipeline events and create notifications for them.

    Runs periodically in a background thread. Only creates notifications
    for events that haven't been notified yet.
    """
    global _last_notification_check
    now = datetime.now(timezone.utc)
    since = _last_notification_check or (now - timedelta(hours=24))
    _last_notification_check = now

    session = db.SessionLocal()
    created = 0
    try:
        for f in session.query(models.Finding).filter(models.Finding.created_at >= since).all():
            existing = session.query(models.Notification).filter(
                models.Notification.notification_type == "finding_alert",
                models.Notification.linked_type == "finding",
                models.Notification.linked_id == f.id,
            ).first()
            if not existing:
                session.add(models.Notification(
                    notification_type="finding_alert",
                    message=f"New finding: {f.title or f'Finding #{f.id}'}",
                    linked_type="finding", linked_id=f.id,
                ))
                created += 1

        for s in session.query(models.ScanRun).filter(models.ScanRun.started_at >= since).all():
            if s.finished_at:
                existing = session.query(models.Notification).filter(
                    models.Notification.notification_type == "scan_complete",
                    models.Notification.linked_type == "scan",
                    models.Notification.linked_id == s.id,
                ).first()
                if not existing:
                    status_text = "completed" if s.status == "completed" else s.status or "finished"
                    session.add(models.Notification(
                        notification_type="scan_complete",
                        message=f"Scan #{s.id} {status_text} — {s.endpoint_count or 0} endpoints",
                        linked_type="scan", linked_id=s.id,
                    ))
                    created += 1

        if created:
            session.commit()
    except Exception as exc:
        logger.warning("Notification generator error: %s", exc)
    finally:
        session.close()
    return created


@router.post("/notifications/generate")
def trigger_notification_generation():
    """Manually trigger notification generation from recent pipeline events."""
    c = _generate_notifications()
    return {"generated": c, "status": "ok"}


def _notification_poller_loop(interval: int = 120):
    """Background daemon thread that polls for new events to notify about."""
    # Wait before first poll so database has time to initialize (avoids spurious
    # warnings when the module is imported before init_db() runs).
    time.sleep(interval)
    while True:
        try:
            c = _generate_notifications()
            if c:
                logger.info("Generated %d notifications", c)
        except Exception:
            pass
        time.sleep(interval)


def start_notification_poller():
    """Start the background notification poller thread.

    Call this during application startup, not at module level,
    to avoid spawning threads on import.
    """
    t = threading.Thread(target=_notification_poller_loop, daemon=True)
    t.start()
    logger.info("Notification poller thread started")
