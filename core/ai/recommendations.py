"""
Recommendation Engine — Rastro

Generates actionable recommendations from real system data.
Each recommendation answers: what to do, why, and what's the expected value.
"""

from __future__ import annotations

from typing import Any, Dict, List

from database import db, models
from core.engine.unified_scoring import score as unified_score, score_target as unified_score_target
from core.engine.unified_scoring import generate_suggestions


def generate_recommendations() -> List[Dict[str, Any]]:
    session = db.SessionLocal()
    try:
        recs: List[Dict[str, Any]] = []
        targets = session.query(models.Target).all()
        endpoints = session.query(models.Endpoint).all()
        findings = session.query(models.Finding).all()
        verdicts = session.query(models.Verdict).all()

        for t in targets:
            t_eps = [ep for ep in endpoints if ep.target_id == t.id]
            if not t_eps:
                continue

            t_findings = [f for f in findings if f.target_id == t.id]
            t_verdicts = [v for v in verdicts if v.endpoint_id and v.endpoint_id in {ep.id for ep in t_eps}]

            roi = unified_score_target({
                "api_count": len(t_eps),
                "has_graphql": any("/graphql" in (ep.path or "").lower() for ep in t_eps),
                "has_admin": any("admin" in (ep.path or "").lower() for ep in t_eps),
                "has_api": any("/api/" in (ep.path or "") for ep in t_eps),
                "has_exports": any("export" in (ep.path or "").lower() for ep in t_eps),
                "source": (t.name or "").lower(),
            })

            critical_eps = []
            idor_eps = []
            graphql_eps = []
            actionable_eps = []
            for ep in t_eps:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                rs = s.get("risk_score", 0)
                if rs >= 50:
                    critical_eps.append({"path": ep.path, "method": ep.method, "score": rs})
                if s.get("potential_idor"):
                    idor_eps.append({"path": ep.path, "method": ep.method, "score": rs})
                if "graphql" in (ep.path or "").lower():
                    graphql_eps.append({"path": ep.path, "method": ep.method})
                if s.get("actionable"):
                    actionable_eps.append({
                        "path": ep.path,
                        "method": ep.method,
                        "score": rs,
                        "suggestions": generate_suggestions(ep.path, ep.method or "GET", ep.parsed_params),
                    })

            confirmed = sum(1 for v in t_verdicts if v.status == "confirmed")
            estimated_payout = confirmed * 5000 + len(critical_eps) * 3000 + len(idor_eps) * 2000
            time_estimate = max(30, len(actionable_eps) * 15 + len(critical_eps) * 20)

            priority = roi.get("priority", 0)
            if priority >= 50 or len(critical_eps) > 0:
                recs.append({
                    "type": "attack",
                    "target_id": t.id,
                    "target_name": t.name,
                    "domain": t.domain,
                    "priority_score": priority,
                    "roi_score": roi.get("roi_score", 0),
                    "quality": roi.get("quality", 0),
                    "complexity": roi.get("complexity_score", 0),
                    "critical_endpoints": len(critical_eps),
                    "idor_candidates": len(idor_eps),
                    "graphql_surfaces": len(graphql_eps),
                    "actionable_endpoints": len(actionable_eps),
                    "estimated_time_minutes": time_estimate,
                    "estimated_payout": estimated_payout,
                    "confirmed_findings": confirmed,
                    "top_critical": critical_eps[:3],
                    "top_idor": idor_eps[:3],
                    "top_actionable": actionable_eps[:3],
                    "reason": (
                        f"ROI {roi.get('roi_score', 0):.0f} · "
                        f"{len(critical_eps)} críticos · "
                        f"{len(idor_eps)} IDOR potenciales · "
                        f"{len(graphql_eps)} GraphQL"
                    ),
                })

        recs.sort(key=lambda r: r.get("priority_score", 0), reverse=True)
        return recs
    finally:
        session.close()


def get_best_recommendation() -> Dict[str, Any]:
    recs = generate_recommendations()
    if recs:
        return recs[0]
    return {
        "type": "no_recommendations",
        "target_name": "",
        "priority_score": 0,
        "reason": "No hay datos suficientes para generar recomendaciones. Agrega targets primero.",
        "estimated_time_minutes": 0,
        "estimated_payout": 0,
    }
