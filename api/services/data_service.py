from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from database import db, models
from core.targets.models import TargetIntel
from core.engine.unified_scoring import score as unified_score
from core.engine.unified_scoring import score_target as unified_score_target

SEVERITY_PAYOUT = {
    "critical": 25000,
    "high": 10000,
    "medium": 3000,
    "low": 500,
    "info": 0,
}

ALLOWED_SORT_COLS = {
    "targets": {"id", "name", "domain", "created_at"},
    "endpoints": {"id", "target_id", "path", "method", "risk_score", "confidence"},
    "findings": {"id", "target_id", "endpoint_id", "title", "severity", "created_at"},
    "evidence": {"id", "verdict_id", "response_status", "consistent"},
    "opportunities": {"roi", "max_risk", "estimated_payout", "opportunity_score"},
}


def _get_session():
    db.init_db()
    return db.SessionLocal()


def _apply_sorting(q, model_cls, sort_by: str, sort_order: str, allowed: set) -> Any:
    if sort_by in allowed and hasattr(model_cls, sort_by):
        col = getattr(model_cls, sort_by)
        return q.order_by(col.desc() if sort_order == "desc" else col.asc())
    return q


def _apply_search(q, model_cls, search: str, fields: List[str]) -> Any:
    if not search:
        return q
    from sqlalchemy import or_
    conditions = []
    for field in fields:
        if hasattr(model_cls, field):
            col = getattr(model_cls, field)
            conditions.append(col.ilike(f"%{search}%"))
    if conditions:
        q = q.filter(or_(*conditions))
    return q


def list_targets(skip: int = 0, limit: int = 100, sort_by: str = "name", sort_order: str = "asc", search: str = "") -> Tuple[List[Dict[str, Any]], int]:
    session = _get_session()
    try:
        query = session.query(models.Target)
        query = _apply_search(query, models.Target, search, ["name", "domain"])
        query = _apply_sorting(query, models.Target, sort_by, sort_order, ALLOWED_SORT_COLS["targets"])
        total = query.count()
        targets = query.offset(skip).limit(limit).all()
        result = []
        for t in targets:
            endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).all()
            findings = session.query(models.Finding).filter(models.Finding.target_id == t.id).all()
            scores = [_score_endpoint(ep) for ep in endpoints]

            max_risk = max((s.get("risk_score", 0) for s in scores), default=0)
            payout = sum(_estimated_payout(f, t.id) for f in findings)

            confirmed = 0
            for f in findings:
                if f.endpoint_id:
                    v = session.query(models.Verdict).filter(
                        models.Verdict.endpoint_id == f.endpoint_id,
                        models.Verdict.status == "confirmed",
                    ).first()
                    if v:
                        confirmed += 1

            result.append({
                "id": t.id,
                "name": t.name or f"Target #{t.id}",
                "domain": t.domain or "",
                "endpoint_count": len(endpoints),
                "finding_count": len(findings),
                "confirmed_findings": confirmed,
                "estimated_payout": payout,
                "roi": round(_target_roi(t, endpoints) / 10, 1),
                "risk_score": max_risk,
                "opportunity_score": 0.0,
                "competition_score": 0,
                "freshness_score": 0,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return result, total
    finally:
        session.close()


def get_target(target_id: int) -> Optional[Dict[str, Any]]:
    session = _get_session()
    try:
        t = session.query(models.Target).filter(models.Target.id == target_id).first()
        if not t:
            return None
        endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).all()
        findings = session.query(models.Finding).filter(models.Finding.target_id == t.id).all()
        scores = [_score_endpoint(ep) for ep in endpoints]

        max_risk = max((s.get("risk_score", 0) for s in scores), default=0)
        payout = sum(_estimated_payout(f, t.id) for f in findings)

        surfaces = set()
        vectors = set()
        for s in scores:
            for surf in s.get("attack_surface", []):
                surfaces.add(surf)
            vectors.add(s.get("vector", "unknown"))

        confirmed = 0
        for f in findings:
            if f.endpoint_id:
                v = session.query(models.Verdict).filter(
                    models.Verdict.endpoint_id == f.endpoint_id,
                    models.Verdict.status == "confirmed",
                ).first()
                if v:
                    confirmed += 1

        intel = session.query(TargetIntel).filter(TargetIntel.id == target_id).first()

        return {
            "id": t.id,
            "name": t.name or f"Target #{t.id}",
            "domain": t.domain or "",
            "endpoint_count": len(endpoints),
            "finding_count": len(findings),
            "confirmed_count": confirmed,
            "estimated_payout": payout,
            "roi": round(_target_roi(t, endpoints) / 10, 1),
            "max_risk": max_risk,
            "surfaces": sorted(surfaces),
            "vectors": sorted(vectors),
            "opportunity_score": round((intel.opportunity_score or 0) / 10, 1) if intel else 0,
            "competition_score": int(intel.competition_score or 0) if intel else 0,
            "freshness_score": int(intel.freshness_score or 0) if intel else 50,
        }
    finally:
        session.close()


def list_endpoints(target_id: Optional[int] = None, skip: int = 0, limit: int = 100, sort_by: str = "path", sort_order: str = "asc", search: str = "") -> Tuple[List[Dict[str, Any]], int]:
    session = _get_session()
    try:
        q = session.query(models.Endpoint)
        if target_id is not None:
            q = q.filter(models.Endpoint.target_id == target_id)
        q = _apply_search(q, models.Endpoint, search, ["path", "method"])
        q = _apply_sorting(q, models.Endpoint, sort_by, sort_order, ALLOWED_SORT_COLS["endpoints"])
        total = q.count()
        endpoints = q.offset(skip).limit(limit).all()
        result = []
        for ep in endpoints:
            s = _score_endpoint(ep)
            result.append({
                "id": ep.id,
                "target_id": ep.target_id,
                "path": ep.path,
                "method": ep.method or "GET",
                "risk_score": s.get("risk_score", 0),
                "confidence": s.get("confidence", 0),
                "vector": s.get("vector", "unknown"),
                "labels": s.get("labels", []),
                "signals": s.get("signals", []),
                "attack_surface": s.get("attack_surface", []),
                "actionable": s.get("actionable", False),
            })
        return result, total
    finally:
        session.close()


def get_endpoint(endpoint_id: int) -> Optional[Dict[str, Any]]:
    session = _get_session()
    try:
        ep = session.query(models.Endpoint).filter(models.Endpoint.id == endpoint_id).first()
        if not ep:
            return None
        s = _score_endpoint(ep)
        return {
            "id": ep.id,
            "target_id": ep.target_id,
            "path": ep.path,
            "method": ep.method or "GET",
            "risk_score": s.get("risk_score", 0),
            "confidence": s.get("confidence", 0),
            "vector": s.get("vector", "unknown"),
            "labels": s.get("labels", []),
            "signals": s.get("signals", []),
            "attack_surface": s.get("attack_surface", []),
            "actionable": s.get("actionable", False),
        }
    finally:
        session.close()


def list_findings(target_id: Optional[int] = None, endpoint_id: Optional[int] = None, skip: int = 0, limit: int = 100, sort_by: str = "severity", sort_order: str = "desc", search: str = "") -> Tuple[List[Dict[str, Any]], int]:
    session = _get_session()
    try:
        q = session.query(models.Finding)
        if target_id is not None:
            q = q.filter(models.Finding.target_id == target_id)
        if endpoint_id is not None:
            q = q.filter(models.Finding.endpoint_id == endpoint_id)
        q = _apply_search(q, models.Finding, search, ["title", "severity"])
        q = _apply_sorting(q, models.Finding, sort_by, sort_order, ALLOWED_SORT_COLS["findings"])
        total = q.count()
        findings = q.offset(skip).limit(limit).all()
        result = []
        for f in findings:
            target = session.query(models.Target).filter(models.Target.id == f.target_id).first()
            ep = None
            if f.endpoint_id:
                ep = session.query(models.Endpoint).filter(models.Endpoint.id == f.endpoint_id).first()
            result.append({
                "id": f.id,
                "target_id": f.target_id,
                "endpoint_id": f.endpoint_id,
                "title": f.title or f"Finding #{f.id}",
                "severity": f.severity or "medium",
                "description": f.description,
                "payout": _estimated_payout(f, f.target_id),
                "target_name": target.name or f"#{target.id}" if target else "",
                "endpoint_path": f"{ep.method} {ep.path}" if ep else "",
                "created_at": f.created_at.isoformat() if f.created_at else None,
            })
        return result, total
    finally:
        session.close()


def list_evidence(verdict_id: Optional[int] = None, skip: int = 0, limit: int = 100, sort_by: str = "id", sort_order: str = "desc", search: str = "") -> Tuple[List[Dict[str, Any]], int]:
    session = _get_session()
    try:
        q = session.query(models.Evidence)
        if verdict_id is not None:
            q = q.filter(models.Evidence.verdict_id == verdict_id)
        q = _apply_search(q, models.Evidence, search, ["attempt_label", "request_url"])
        q = _apply_sorting(q, models.Evidence, sort_by, sort_order, ALLOWED_SORT_COLS["evidence"])
        total = q.count()
        evidence = q.offset(skip).limit(limit).all()
        items = [
            {
                "id": e.id,
                "verdict_id": e.verdict_id,
                "endpoint_id": e.endpoint_id,
                "attempt_label": e.attempt_label or "",
                "request_url": e.request_url or "",
                "request_method": e.request_method or "GET",
                "response_status": e.response_status,
                "consistent": e.consistent == "true",
                "curl_command": e.curl_command,
                "body_diff_ratio": float(e.body_diff_ratio) if e.body_diff_ratio else 0.0,
            }
            for e in evidence
        ]
        return items, total
    finally:
        session.close()


def list_opportunities(skip: int = 0, limit: int = 200, sort_by: str = "roi", sort_order: str = "desc", search: str = "") -> Tuple[List[Dict[str, Any]], int]:
    session = _get_session()
    try:
        targets = session.query(models.Target).all()
        if search:
            targets = [t for t in targets if search.lower() in (t.name or "").lower() or search.lower() in (t.domain or "").lower()]
        scored = []
        for t in targets:
            endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).all()
            if not endpoints:
                continue
            findings = session.query(models.Finding).filter(models.Finding.target_id == t.id).all()

            max_risk = 0.0
            surfaces = set()
            vectors = set()
            for ep in endpoints:
                s = _score_endpoint(ep)
                rs = s.get("risk_score", 0.0)
                if rs > max_risk:
                    max_risk = rs
                for surf in s.get("attack_surface", []):
                    surfaces.add(surf)
                vectors.add(s.get("vector", "unknown"))

            payout = sum(_estimated_payout(f, t.id) for f in findings)
            roi = _target_roi(t, endpoints) / 10
            intel = session.query(TargetIntel).filter(TargetIntel.id == t.id).first()

            scored.append({
                "target_id": t.id,
                "name": t.name or f"Target #{t.id}",
                "domain": t.domain or "",
                "roi": round(roi, 1),
                "max_risk": max_risk,
                "endpoint_count": len(endpoints),
                "finding_count": len(findings),
                "surfaces": sorted(surfaces)[:4],
                "vectors": sorted(vectors),
                "estimated_payout": payout,
                "opportunity_score": round((intel.opportunity_score or 0) / 10, 1) if intel else 0,
                "competition_score": int(intel.competition_score or 0) if intel else 0,
                "freshness_score": int(intel.freshness_score or 0) if intel else 50,
            })
        reverse = sort_order == "desc"
        scored.sort(key=lambda r: r.get(sort_by, 0) if isinstance(r.get(sort_by, 0), (int, float)) else str(r.get(sort_by, "")), reverse=reverse)
        total = len(scored)
        scored = scored[skip:skip + limit]
        return scored, total
    finally:
        session.close()


def get_attack_surfaces() -> Dict[str, List[Dict[str, Any]]]:
    session = _get_session()
    try:
        endpoints = session.query(models.Endpoint).all()
        groups = {}
        for ep in endpoints:
            s = _score_endpoint(ep)
            surfaces = s.get("attack_surface", [])
            if not surfaces:
                surfaces = ["general"]
            for surface in surfaces:
                groups.setdefault(surface, []).append({
                    "id": ep.id,
                    "target_id": ep.target_id,
                    "path": ep.path,
                    "method": ep.method or "GET",
                    "risk_score": s.get("risk_score", 0),
                    "confidence": s.get("confidence", 0),
                    "vector": s.get("vector", "unknown"),
                    "labels": s.get("labels", []),
                    "signals": s.get("signals", []),
                    "attack_surface": s.get("attack_surface", []),
                    "actionable": s.get("actionable", False),
                })
        for k in groups:
            groups[k].sort(key=lambda x: x["risk_score"], reverse=True)
        return dict(sorted(groups.items()))
    finally:
        session.close()


def get_pipeline_stages() -> Dict[str, List[Dict[str, Any]]]:
    session = _get_session()
    try:
        stages = {"detected": [], "validated": [], "confirmed": [], "reported": []}
        endpoints = session.query(models.Endpoint).all()
        findings = session.query(models.Finding).all()
        verdicts = session.query(models.Verdict).all()

        endpoint_verdicts = {}
        for v in verdicts:
            if v.endpoint_id:
                endpoint_verdicts.setdefault(v.endpoint_id, []).append(v)

        for f in findings:
            target = session.query(models.Target).filter(models.Target.id == f.target_id).first()
            item = {
                "id": f.id,
                "target_id": f.target_id,
                "endpoint_id": f.endpoint_id,
                "title": f.title or f"Finding #{f.id}",
                "severity": f.severity or "medium",
                "description": f.description,
                "payout": _estimated_payout(f, f.target_id),
                "target_name": target.name or f"#{target.id}" if target else "",
                "endpoint_path": "",
            }
            if f.endpoint_id:
                ep = next((e for e in endpoints if e.id == f.endpoint_id), None)
                if ep:
                    item["endpoint_path"] = f"{ep.method} {ep.path}"

            ep_verdicts = endpoint_verdicts.get(f.endpoint_id or 0, [])
            if any(v.status == "confirmed" for v in ep_verdicts):
                stages["confirmed"].append(item)
            elif any(v.status == "inconclusive" for v in ep_verdicts) or ep_verdicts:
                stages["validated"].append(item)
            else:
                stages["detected"].append(item)

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        for stage in stages.values():
            stage.sort(key=lambda x: severity_order.get(x["severity"], 5))
        return stages
    finally:
        session.close()


def generate_report() -> Dict[str, Any]:
    session = _get_session()
    try:
        findings = session.query(models.Finding).all()
        targets = session.query(models.Target).all()
        verdicts = session.query(models.Verdict).all()

        confirmed_ep_ids = set()
        for v in verdicts:
            if v.status == "confirmed" and v.endpoint_id:
                confirmed_ep_ids.add(v.endpoint_id)

        confirmed_findings = [f for f in findings if f.endpoint_id in confirmed_ep_ids]
        total_value = sum(SEVERITY_PAYOUT.get((f.severity or "info").lower(), 0) for f in findings)

        from datetime import datetime as dt
        now = dt.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            "# Rastro Bug Bounty Report\n",
            f"*Generated: {now}*\n",
            "---\n",
            "## Summary\n",
            f"- **Total Findings:** {len(findings)}\n",
            f"- **Confirmed Findings:** {len(confirmed_findings)}\n",
            f"- **Estimated Total Value:** ${total_value:,}\n",
            f"- **Targets Analyzed:** {len(targets)}\n",
            "---\n",
            "## Findings\n\n",
        ]
        finding_outs = []
        for f in confirmed_findings:
            target = next((t for t in targets if t.id == f.target_id), None)
            payout = _estimated_payout(f, f.target_id)
            lines.append(f"### {f.title or f'Finding #{f.id}'}\n")
            lines.append(f"- **Target:** {target.name if target else f'#{f.target_id}'}\n")
            lines.append(f"- **Severity:** {f.severity}\n")
            lines.append(f"- **Estimated Payout:** ${payout:,}\n")
            if f.description:
                lines.append(f"- **Description:** {f.description}\n")
            lines.append("\n")
            finding_outs.append({
                "id": f.id,
                "target_id": f.target_id,
                "endpoint_id": f.endpoint_id,
                "title": f.title or f"Finding #{f.id}",
                "severity": f.severity or "medium",
                "description": f.description,
                "payout": payout,
                "target_name": target.name if target else "",
                "endpoint_path": "",
            })

        return {
            "title": "Rastro Bug Bounty Report",
            "summary": f"{len(confirmed_findings)} confirmed findings across {len(targets)} targets",
            "findings": finding_outs,
            "total_findings": len(confirmed_findings),
            "total_estimated_value": total_value,
            "generated_at": now,
            "markdown": "".join(lines),
        }
    finally:
        session.close()


# ── Internal helpers ────────────────────────────────────

def _score_endpoint(ep) -> dict:
    return unified_score(ep.path, ep.method or "GET", ep.parsed_params)


def _estimated_payout(finding, target_id: int) -> int:
    base = SEVERITY_PAYOUT.get((finding.severity or "info").lower(), 0)
    session = _get_session()
    try:
        intel = session.query(TargetIntel).filter(TargetIntel.id == target_id).first()
        if intel and intel.reward_score:
            base = int(base * (1 + intel.reward_score / 100))
        return base
    finally:
        session.close()


def _target_roi(target, endpoints) -> float:
    if not endpoints:
        return 0.0
    api_count = len(endpoints)
    has_graphql = any("/graphql" in (e.path or "").lower() for e in endpoints)
    has_admin = any("admin" in (e.path or "").lower() for e in endpoints)
    has_api = any(e.path and "/api/" in e.path for e in endpoints)
    has_exports = any("export" in (e.path or "").lower() for e in endpoints)
    meta = {
        "api_count": api_count,
        "has_graphql": has_graphql,
        "has_admin": has_admin,
        "has_api": has_api,
        "has_exports": has_exports,
        "source": (target.name or "").lower(),
    }
    res = unified_score_target(meta)
    return res.get("roi_score", 0.0)
