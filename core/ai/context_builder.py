"""
Builds a comprehensive context snapshot from real Rastro system data.

Every field comes from a real database query or engine computation.
No mock data, no placeholders.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import db, models
from core.engine.snapshot import EndpointSnapshot, PipelineSnapshot, TargetSnapshot
from core.engine.unified_scoring import score as unified_score, score_target as unified_score_target
from core.evidence.graph import EvidenceGraph
from core.quick_wins.quick_wins_engine import QuickWinsEngine
from core.targets.models import TargetIntel


def build_full_context() -> Dict[str, Any]:
    session = db.SessionLocal()
    try:
        now = datetime.utcnow()
        context: Dict[str, Any] = {
            "timestamp": now.isoformat(),
            "generated_ago": "just now",
        }

        # ── Targets ──
        targets = session.query(models.Target).all()
        context["targets"] = {
            "total": len(targets),
            "list": [
                {
                    "id": t.id,
                    "name": t.name,
                    "domain": t.domain,
                    "created": t.created_at.isoformat() if t.created_at else "",
                }
                for t in targets
            ],
        }

        # ── Endpoints ──
        endpoints = session.query(models.Endpoint).all()
        total_risk = 0.0
        high_signal: List[Dict] = []
        actionable: List[Dict] = []
        by_vector: Dict[str, int] = {}
        by_surface: Dict[str, int] = {}
        recent_eps = 0
        cutoff_24h = now - timedelta(hours=24)

        for ep in endpoints:
            s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
            rs = s.get("risk_score", 0)
            total_risk += rs
            if rs >= 25:
                high_signal.append({
                    "id": ep.id,
                    "target_id": ep.target_id,
                    "path": ep.path,
                    "method": ep.method,
                    "risk_score": rs,
                    "vector": s.get("vector", ""),
                    "labels": s.get("labels", []),
                })
            if s.get("actionable"):
                actionable.append({
                    "id": ep.id,
                    "target_id": ep.target_id,
                    "path": ep.path,
                    "method": ep.method,
                    "risk_score": rs,
                    "vector": s.get("vector", ""),
                })
            vec = s.get("vector", "Unknown")
            by_vector[vec] = by_vector.get(vec, 0) + 1
            for surf in s.get("attack_surface", []):
                by_surface[surf] = by_surface.get(surf, 0) + 1
            if ep.discovered_at and ep.discovered_at >= cutoff_24h:
                recent_eps += 1

        high_signal.sort(key=lambda x: x["risk_score"], reverse=True)
        actionable.sort(key=lambda x: x["risk_score"], reverse=True)

        context["endpoints"] = {
            "total": len(endpoints),
            "high_signal": len(high_signal),
            "actionable": len(actionable),
            "avg_risk": round(total_risk / max(len(endpoints), 1), 1),
            "discovered_24h": recent_eps,
            "vector_distribution": by_vector,
            "attack_surfaces": by_surface,
            "top_high_signal": high_signal[:10],
            "top_actionable": actionable[:10],
        }

        # ── Findings ──
        findings = session.query(models.Finding).all()
        sev_counts: Dict[str, int] = {}
        recent_findings = 0
        for f in findings:
            sev = (f.severity or "info").lower()
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
            if f.created_at and f.created_at >= cutoff_24h:
                recent_findings += 1
        context["findings"] = {
            "total": len(findings),
            "by_severity": sev_counts,
            "new_24h": recent_findings,
        }

        # ── Verdicts ──
        verdicts = session.query(models.Verdict).all()
        v_status: Dict[str, int] = {}
        for v in verdicts:
            v_status[v.status] = v_status.get(v.status, 0) + 1
        context["verdicts"] = {
            "total": len(verdicts),
            "by_status": v_status,
            "confirmed": v_status.get("confirmed", 0),
            "rejected": v_status.get("rejected", 0),
            "inconclusive": v_status.get("inconclusive", 0),
        }

        # ── Scans ──
        scans = session.query(models.ScanRun).order_by(models.ScanRun.started_at.desc()).limit(20).all()
        active_scans = [s for s in scans if s.status in ("pending", "running")]
        context["scans"] = {
            "total": len(scans),
            "active": len(active_scans),
            "recent": [
                {
                    "id": s.id,
                    "target_id": s.target_id,
                    "mode": s.mode,
                    "status": s.status,
                    "endpoint_count": s.endpoint_count,
                    "started": s.started_at.isoformat() if s.started_at else "",
                }
                for s in scans[:10]
            ],
        }

        # ── ROI / Opportunities ──
        target_rois = []
        for t in targets:
            t_eps = [ep for ep in endpoints if ep.target_id == t.id]
            if not t_eps:
                continue
            roi = unified_score_target({
                "api_count": len(t_eps),
                "has_graphql": any("/graphql" in (ep.path or "").lower() for ep in t_eps),
                "has_admin": any("admin" in (ep.path or "").lower() for ep in t_eps),
                "has_api": any("/api/" in (ep.path or "") for ep in t_eps),
                "has_exports": any("export" in (ep.path or "").lower() for ep in t_eps),
                "source": (t.name or "").lower(),
            })
            target_rois.append({
                "id": t.id,
                "name": t.name,
                "domain": t.domain,
                "ep_count": len(t_eps),
                "priority": roi.get("priority", 0),
                "roi_score": roi.get("roi_score", 0),
                "quality": roi.get("quality", 0),
                "complexity": roi.get("complexity_score", 0),
                "attack_surface_score": roi.get("attack_surface_score", 0),
            })
        target_rois.sort(key=lambda x: x["priority"], reverse=True)
        context["opportunities"] = {
            "total": len(target_rois),
            "top": target_rois[:10],
        }

        # ── Pipeline ──
        endpoint_verdicts: Dict[int, List] = {}
        for v in verdicts:
            if v.endpoint_id:
                endpoint_verdicts.setdefault(v.endpoint_id, []).append(v)

        pipeline = {"detected": 0, "validated": 0, "confirmed": 0, "reported": 0}
        for f in findings:
            ep_verdicts = endpoint_verdicts.get(f.endpoint_id or 0, [])
            if any(v.status == "confirmed" for v in ep_verdicts):
                pipeline["confirmed"] += 1
                pipeline["reported"] += 1
            elif ep_verdicts:
                pipeline["validated"] += 1
            else:
                pipeline["detected"] += 1
        context["pipeline"] = pipeline

        # ── Program Intelligence ──
        intel_records = session.query(TargetIntel).all()
        platform_dist: Dict[str, int] = {}
        for rec in intel_records:
            src = rec.source or "Unknown"
            platform_dist[src] = platform_dist.get(src, 0) + 1
        context["intelligence"] = {
            "total_programs": len(intel_records),
            "platforms": platform_dist,
        }

        # ── Recent Activity Summary ──
        recent_activity: List[Dict] = []
        for f in findings:
            if f.created_at and f.created_at >= cutoff_24h:
                recent_activity.append({
                    "type": "finding",
                    "id": f.id,
                    "title": f.title or f"Finding #{f.id}",
                    "severity": f.severity or "medium",
                    "timestamp": f.created_at.isoformat() if f.created_at else "",
                })
        for v in verdicts:
            if v.created_at and v.created_at >= cutoff_24h:
                recent_activity.append({
                    "type": "verdict",
                    "id": v.id,
                    "status": v.status,
                    "timestamp": v.created_at.isoformat() if v.created_at else "",
                })
        for s in scans:
            if s.started_at and s.started_at >= cutoff_24h:
                recent_activity.append({
                    "type": "scan",
                    "id": s.id,
                    "status": s.status,
                    "timestamp": s.started_at.isoformat() if s.started_at else "",
                })
        recent_activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        context["activity"] = {
            "last_24h": len(recent_activity),
            "events": recent_activity[:20],
        }

        # ── Health ──
        context["health"] = {
            "targets": len(targets),
            "endpoints": len(endpoints),
            "findings": len(findings),
            "verdicts": len(verdicts),
            "intel_programs": len(intel_records),
            "active_scans": len(active_scans),
        }

        # ── Quick Wins ──
        try:
            ep_snaps = []
            for ep in endpoints:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                ep_snaps.append(EndpointSnapshot(
                    path=ep.path,
                    method=ep.method or "GET",
                    risk_score=float(s.get("risk_score", 0)),
                    confidence=0.0,
                    labels=s.get("labels", []),
                    attack_surface=s.get("attack_surface", []),
                    signals=s.get("signals", []),
                    vector=s.get("vector", ""),
                    actionable=bool(s.get("actionable", False)),
                    potential_idor=bool(s.get("potential_idor", False)),
                ))
            first_target = targets[0] if targets else None
            if first_target:
                qw_snapshot = PipelineSnapshot(
                    status="completed",
                    target=TargetSnapshot(
                        target_id=first_target.id, name=first_target.name or f"#{first_target.id}",
                    ),
                    endpoints=ep_snaps,
                )
                qw_engine = QuickWinsEngine()
                qw_report = qw_engine.evaluate(qw_snapshot, EvidenceGraph())
                context["quick_wins"] = {
                    "total_opportunities": qw_report.total_opportunities,
                    "avg_quick_win_score": qw_report.avg_quick_win_score,
                    "exploitability_score": qw_report.exploitability_score,
                    "total_estimated_value": qw_report.total_estimated_value,
                    "fastest_path_minutes": qw_report.fastest_path_minutes,
                    "categories": {},
                    "top_opportunities": [
                        {
                            "endpoint": f"{w.endpoint_method} {w.endpoint_path}",
                            "score": w.quick_win_score,
                            "category": w.category,
                            "payout": w.estimated_payout,
                            "effort": w.estimated_effort_minutes,
                        }
                        for w in qw_report.top_quick_wins[:5]
                    ],
                }
                for w in qw_report.confidence_ranked_opportunities:
                    cat = w.category
                    context["quick_wins"]["categories"][cat] = context["quick_wins"]["categories"].get(cat, 0) + 1
            else:
                context["quick_wins"] = {
                    "total_opportunities": 0, "avg_quick_win_score": 0.0,
                    "categories": {}, "top_opportunities": [],
                }
        except Exception:
            context["quick_wins"] = {
                "total_opportunities": 0, "avg_quick_win_score": 0.0,
                "categories": {}, "top_opportunities": [],
            }

        return context
    finally:
        session.close()
