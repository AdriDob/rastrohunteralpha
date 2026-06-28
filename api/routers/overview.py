from __future__ import annotations

import contextlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func as sa_func

from core_engines.engine.unified_scoring import score as unified_score
from core_engines.engine.unified_scoring import score_target as unified_score_target
from core_engines.gateway.schemas import safe_response
from core_engines.targets.models import TargetIntel
from database import db, models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview")
def get_overview():
    session = db.SessionLocal()
    try:
        target_count = session.query(models.Target).count()
        endpoint_count = session.query(models.Endpoint).count()
        finding_count = session.query(models.Finding).count()
        active_scans = session.query(models.ScanRun).filter(
            models.ScanRun.status.in_(["pending", "running"])
        ).count()
        confirmed_count = session.query(models.Verdict).filter(
            models.Verdict.status == "confirmed"
        ).count()

        # Risk/vector distribution — deduplicate by (path, method) to minimise scoring calls
        high_signal = 0
        total_risk = 0.0
        risk_buckets: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        vector_dist: dict[str, int] = {}
        endpoint_target_ids: dict[int, int] = {}
        _score_cache: dict[tuple[str, str], dict[str, Any]] = {}

        for ep in session.query(models.Endpoint.path, models.Endpoint.method, models.Endpoint.params, models.Endpoint.target_id, models.Endpoint.id).all():
            ep_params = {}
            if ep.params:
                with contextlib.suppress(json.JSONDecodeError, ValueError):
                    ep_params = json.loads(ep.params)
            key = (ep.path or "/", ep.method or "GET")
            if key not in _score_cache:
                _score_cache[key] = unified_score(*key, ep_params)
            s = _score_cache[key]
            rs = s.get("risk_score", 0)
            total_risk += rs
            endpoint_target_ids[ep.id] = ep.target_id
            if rs >= 50:
                risk_buckets["critical"] += 1
                high_signal += 1
            elif rs >= 25:
                risk_buckets["high"] += 1
                high_signal += 1
            elif rs >= 10:
                risk_buckets["medium"] += 1
            elif rs >= 1:
                risk_buckets["low"] += 1
            else:
                risk_buckets["info"] += 1
            vec = s.get("vector", "Unknown")
            vector_dist[vec] = vector_dist.get(vec, 0) + 1

        avg_risk = round(total_risk / max(endpoint_count, 1), 1)

        # Severity counts — SQL GROUP BY
        severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for row in session.query(models.Finding.severity, sa_func.count(models.Finding.id)).group_by(models.Finding.severity).all():
            sev = (row[0] or "info").lower()
            severity_counts[sev] = row[1]

        # Pipeline stages — single query for finding + verdict status
        pipeline_stages = {"detected": 0, "validated": 0, "confirmed": 0, "reported": 0}
        confirmed_ep_ids = {
            v[0] for v in session.query(models.Verdict.endpoint_id).filter(
                models.Verdict.status == "confirmed",
                models.Verdict.endpoint_id.isnot(None),
            ).distinct().all()
        }
        validated_ep_ids = {
            v[0] for v in session.query(models.Verdict.endpoint_id).filter(
                models.Verdict.status != "confirmed",
                models.Verdict.endpoint_id.isnot(None),
            ).distinct().all()
        } - confirmed_ep_ids

        for f in session.query(models.Finding.endpoint_id).all():
            eid = f.endpoint_id
            if eid in confirmed_ep_ids:
                pipeline_stages["confirmed"] += 1
                pipeline_stages["reported"] += 1
            elif eid in validated_ep_ids:
                pipeline_stages["validated"] += 1
            else:
                pipeline_stages["detected"] += 1

        # Top targets — one query per target is unavoidable for scoring, but limit to 10
        targets = session.query(models.Target).limit(10).all()
        top_targets = []
        for t in targets:
            ep_count = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).count()
            ep_paths = [
                row[0] for row in session.query(models.Endpoint.path).filter(models.Endpoint.target_id == t.id).all()
            ]
            roi = unified_score_target({
                "api_count": ep_count,
                "has_graphql": any("/graphql" in (p or "").lower() for p in ep_paths),
                "has_admin": any("admin" in (p or "").lower() for p in ep_paths),
                "has_api": any("/api/" in p for p in ep_paths if p),
                "has_exports": any("export" in (p or "").lower() for p in ep_paths),
                "source": (t.name or "").lower(),
            })
            top_targets.append({
                "id": t.id,
                "name": t.name,
                "domain": t.domain,
                "endpoint_count": ep_count,
                "priority": roi.get("priority", 0),
                "roi_score": roi.get("roi_score", 0),
                "quality": roi.get("quality", 0),
                "complexity_score": roi.get("complexity_score", 0),
                "attack_surface_score": roi.get("attack_surface_score", 0),
            })
        top_targets.sort(key=lambda x: x["priority"], reverse=True)

        return safe_response({
            "target_count": target_count,
            "endpoint_count": endpoint_count,
            "finding_count": finding_count,
            "confirmed_verdicts": confirmed_count,
            "active_scans": active_scans,
            "high_signal_endpoints": high_signal,
            "avg_risk_score": avg_risk,
            "risk_distribution": risk_buckets,
            "vector_distribution": vector_dist,
            "severity_counts": severity_counts,
            "pipeline_stages": pipeline_stages,
            "top_targets": top_targets[:10],
        })
    finally:
        session.close()


@router.get("/activity")
def get_activity(
    limit: int = Query(20, ge=1, le=100),
    hours: int = Query(72, ge=1, le=720),
):
    session = db.SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        events: list[dict[str, Any]] = []

        for f in session.query(models.Finding).filter(models.Finding.created_at >= since).all():
            events.append({
                "type": "finding",
                "id": f.id,
                "title": f.title or f"Finding #{f.id}",
                "severity": f.severity or "medium",
                "target_id": f.target_id,
                "timestamp": f.created_at.isoformat() if f.created_at else "",
            })

        for v in session.query(models.Verdict).filter(models.Verdict.created_at >= since).all():
            events.append({
                "type": "verdict",
                "id": v.id,
                "status": v.status,
                "hot_path_id": v.hot_path_id,
                "confidence": float(v.confidence) if v.confidence else 0.0,
                "target_id": v.endpoint_id,
                "timestamp": v.created_at.isoformat() if v.created_at else "",
            })

        for s in session.query(models.ScanRun).filter(models.ScanRun.started_at >= since).all():
            events.append({
                "type": "scan",
                "id": s.id,
                "status": s.status,
                "mode": s.mode,
                "endpoint_count": s.endpoint_count,
                "target_id": s.target_id,
                "timestamp": s.started_at.isoformat() if s.started_at else "",
            })

        for e in session.query(models.Evidence).filter(models.Evidence.created_at >= since).all():
            events.append({
                "type": "evidence",
                "id": e.id,
                "verdict_id": e.verdict_id,
                "attempt": e.attempt_label,
                "url": e.request_url,
                "timestamp": e.created_at.isoformat() if e.created_at else "",
            })

        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return safe_response({"events": events[:limit], "total": len(events)})
    finally:
        session.close()


@router.get("/intelligence/summary")
def get_intelligence_summary():
    session = db.SessionLocal()
    try:
        intel_records = session.query(TargetIntel).all()

        platform_dist: dict[str, int] = {}
        qualities: list[float] = []
        complexities: list[float] = []
        rois: list[float] = []
        fresh: list[float] = []
        b2b_count = 0
        saas_count = 0
        graphql_count = 0
        admin_count = 0
        multi_tenant_count = 0

        for rec in intel_records:
            src = rec.source or "Unknown"
            platform_dist[src] = platform_dist.get(src, 0) + 1

            if rec.quality_score is not None:
                qualities.append(float(rec.quality_score))
            if rec.complexity_score is not None:
                complexities.append(float(rec.complexity_score))
            if rec.roi_score is not None:
                rois.append(float(rec.roi_score))
            if rec.freshness_score is not None:
                fresh.append(float(rec.freshness_score))
            if rec.b2b_indicator:
                b2b_count += 1
            if rec.saas_probability and rec.saas_probability > 50:
                saas_count += 1
            if rec.graphql_detected:
                graphql_count += 1
            if rec.admin_detected:
                admin_count += 1
            if rec.multi_tenant:
                multi_tenant_count += 1

        top_platforms = sorted(platform_dist.items(), key=lambda x: x[1], reverse=True)[:8]

        def _avg(vals):
            return round(sum(vals) / max(len(vals), 1), 1) if vals else 0.0

        return safe_response({
            "total_programs": len(intel_records),
            "platform_distribution": dict(top_platforms),
            "avg_quality": _avg(qualities),
            "avg_complexity": _avg(complexities),
            "avg_roi": _avg(rois),
            "avg_freshness": _avg(fresh),
            "b2b_count": b2b_count,
            "saas_count": saas_count,
            "graphql_count": graphql_count,
            "admin_count": admin_count,
            "multi_tenant_count": multi_tenant_count,
        })
    finally:
        session.close()


@router.get("/system/health")
def get_system_health():
    session = db.SessionLocal()
    try:
        target_count = session.query(models.Target).count()
        endpoint_count = session.query(models.Endpoint).count()
        finding_count = session.query(models.Finding).count()
        verdict_count = session.query(models.Verdict).count()
        intel_count = session.query(TargetIntel).count()

        confirmed_verdicts = session.query(models.Verdict).filter(models.Verdict.status == "confirmed").count()
        active_scans = session.query(models.ScanRun).filter(models.ScanRun.status.in_(["pending", "running"])).count()

        last_scan = session.query(models.ScanRun).order_by(models.ScanRun.started_at.desc()).first()
        last_finding = session.query(models.Finding).order_by(models.Finding.created_at.desc()).first()

        result = {
            "status": "healthy",
            "uptime_hint": "API is running",
            "database": {
                "targets": target_count,
                "endpoints": endpoint_count,
                "findings": finding_count,
                "verdicts": verdict_count,
                "intel_programs": intel_count,
            },
            "pipeline": {
                "confirmed_verdicts": confirmed_verdicts,
                "active_scans": active_scans,
            },
            "last_activity": {
                "last_scan": last_scan.started_at.isoformat() if last_scan and last_scan.started_at else None,
                "last_finding": last_finding.created_at.isoformat() if last_finding and last_finding.created_at else None,
            },
        }

        from core_engines.system_health import collect_health
        try:
            detailed = collect_health()
            result["detailed"] = detailed.to_dict()
        except Exception as e:
            logger.warning("Health check collection failed: %s", e)

        return safe_response(result)
    finally:
        session.close()
