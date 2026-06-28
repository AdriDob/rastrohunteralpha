from __future__ import annotations

from typing import Any

from core_engines.engine.unified_scoring import score as unified_score
from core_engines.engine.unified_scoring import score_target as unified_score_target
from core_engines.targets.models import TargetIntel
from database import db, models

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


def _apply_search(q, model_cls, search: str, fields: list[str]) -> Any:
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


def list_targets(skip: int = 0, limit: int = 100, sort_by: str = "name", sort_order: str = "asc", search: str = "") -> tuple[list[dict[str, Any]], int]:
    session = _get_session()
    try:
        query = session.query(models.Target)
        query = _apply_search(query, models.Target, search, ["name", "domain"])
        query = _apply_sorting(query, models.Target, sort_by, sort_order, ALLOWED_SORT_COLS["targets"])
        total = query.count()
        targets = query.offset(skip).limit(limit).all()
        if not targets:
            return [], total

        target_ids = [t.id for t in targets]

        # Batch-load endpoints and findings for all targets
        all_endpoints = {tid: [] for tid in target_ids}
        for ep in session.query(models.Endpoint).filter(models.Endpoint.target_id.in_(target_ids)).all():
            all_endpoints.setdefault(ep.target_id, []).append(ep)

        all_findings = {tid: [] for tid in target_ids}
        for f in session.query(models.Finding).filter(models.Finding.target_id.in_(target_ids)).all():
            all_findings.setdefault(f.target_id, []).append(f)

        # Batch-load confirmed verdict endpoint_ids
        confirmed_endpoint_ids = {
            v[0] for v in session.query(models.Verdict.endpoint_id).filter(
                models.Verdict.status == "confirmed",
                models.Verdict.endpoint_id.isnot(None),
            ).distinct().all()
        }

        # Batch-load TargetIntel for all targets
        intel_map = {}
        for intel in session.query(TargetIntel).filter(TargetIntel.id.in_(target_ids)).all():
            intel_map[intel.id] = intel

        result = []
        for t in targets:
            endpoints = all_endpoints.get(t.id, [])
            findings = all_findings.get(t.id, [])
            scores = [_score_endpoint(ep) for ep in endpoints]

            max_risk = max((s.get("risk_score", 0) for s in scores), default=0)
            payout = sum(SEVERITY_PAYOUT.get((f.severity or "info").lower(), 0) for f in findings)
            intel = intel_map.get(t.id)
            if intel and intel.reward_score:
                payout = int(payout * (1 + intel.reward_score / 100))

            confirmed = sum(1 for f in findings if f.endpoint_id in confirmed_endpoint_ids)

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
                "opportunity_score": round((intel.opportunity_score or 0) / 10, 1) if intel else 0,
                "competition_score": int(intel.competition_score or 0) if intel else 0,
                "freshness_score": int(intel.freshness_score or 0) if intel else 50,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return result, total
    finally:
        session.close()


def get_target(target_id: int) -> dict[str, Any] | None:
    session = _get_session()
    try:
        t = session.query(models.Target).filter(models.Target.id == target_id).first()
        if not t:
            return None
        endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).all()
        findings = session.query(models.Finding).filter(models.Finding.target_id == t.id).all()
        scores = [_score_endpoint(ep) for ep in endpoints]

        max_risk = max((s.get("risk_score", 0) for s in scores), default=0)
        payout = sum(SEVERITY_PAYOUT.get((f.severity or "info").lower(), 0) for f in findings)

        surfaces = set()
        vectors = set()
        for s in scores:
            for surf in s.get("attack_surface", []):
                surfaces.add(surf)
            vectors.add(s.get("vector", "unknown"))

        # Single query for confirmed verdicts of all findings
        finding_endpoint_ids = [f.endpoint_id for f in findings if f.endpoint_id]
        confirmed_endpoint_ids = set()
        if finding_endpoint_ids:
            confirmed_endpoint_ids = {
                v[0] for v in session.query(models.Verdict.endpoint_id).filter(
                    models.Verdict.endpoint_id.in_(finding_endpoint_ids),
                    models.Verdict.status == "confirmed",
                ).distinct().all()
            }
        confirmed = sum(1 for f in findings if f.endpoint_id in confirmed_endpoint_ids)

        intel = session.query(TargetIntel).filter(TargetIntel.id == target_id).first()

        # Apply intel multiplier to payout
        if intel and intel.reward_score:
            payout = int(payout * (1 + intel.reward_score / 100))

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


def list_endpoints(target_id: int | None = None, skip: int = 0, limit: int = 100, sort_by: str = "path", sort_order: str = "asc", search: str = "") -> tuple[list[dict[str, Any]], int]:
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


def get_endpoint(endpoint_id: int) -> dict[str, Any] | None:
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


def list_findings(target_id: int | None = None, endpoint_id: int | None = None, skip: int = 0, limit: int = 100, sort_by: str = "severity", sort_order: str = "desc", search: str = "") -> tuple[list[dict[str, Any]], int]:
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
        if not findings:
            return [], total

        # Batch-load targets and endpoints
        target_ids = list({f.target_id for f in findings})
        endpoint_ids = list({f.endpoint_id for f in findings if f.endpoint_id})
        targets_map = {}
        for t in session.query(models.Target).filter(models.Target.id.in_(target_ids)).all():
            targets_map[t.id] = t
        endpoints_map = {}
        if endpoint_ids:
            for ep in session.query(models.Endpoint).filter(models.Endpoint.id.in_(endpoint_ids)).all():
                endpoints_map[ep.id] = ep

        # Batch-load TargetIntel for payout multipliers
        intel_map = {}
        for intel in session.query(TargetIntel).filter(TargetIntel.id.in_(target_ids)).all():
            intel_map[intel.id] = intel

        result = []
        for f in findings:
            target = targets_map.get(f.target_id)
            ep = endpoints_map.get(f.endpoint_id) if f.endpoint_id else None
            base_payout = SEVERITY_PAYOUT.get((f.severity or "info").lower(), 0)
            intel = intel_map.get(f.target_id)
            payout = int(base_payout * (1 + intel.reward_score / 100)) if intel and intel.reward_score else base_payout
            result.append({
                "id": f.id,
                "target_id": f.target_id,
                "endpoint_id": f.endpoint_id,
                "title": f.title or f"Finding #{f.id}",
                "severity": f.severity or "medium",
                "description": f.description,
                "payout": payout,
                "target_name": target.name or f"#{target.id}" if target else "",
                "endpoint_path": f"{ep.method} {ep.path}" if ep else "",
                "created_at": f.created_at.isoformat() if f.created_at else None,
            })
        return result, total
    finally:
        session.close()


def list_evidence(verdict_id: int | None = None, skip: int = 0, limit: int = 100, sort_by: str = "id", sort_order: str = "desc", search: str = "") -> tuple[list[dict[str, Any]], int]:
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
                "request_body": e.request_body,
                "response_body": e.response_body,
                "request_headers": e.request_headers,
                "response_headers": e.response_headers,
            }
            for e in evidence
        ]
        return items, total
    finally:
        session.close()


def list_opportunities(skip: int = 0, limit: int = 200, sort_by: str = "roi", sort_order: str = "desc", search: str = "") -> tuple[list[dict[str, Any]], int]:
    session = _get_session()
    try:
        targets = session.query(models.Target).all()
        if search:
            targets = [t for t in targets if search.lower() in (t.name or "").lower() or search.lower() in (t.domain or "").lower()]
        if not targets:
            return [], 0

        target_ids = [t.id for t in targets]
        all_endpoints = {tid: [] for tid in target_ids}
        for ep in session.query(models.Endpoint).filter(models.Endpoint.target_id.in_(target_ids)).all():
            all_endpoints.setdefault(ep.target_id, []).append(ep)
        all_findings = {tid: [] for tid in target_ids}
        for f in session.query(models.Finding).filter(models.Finding.target_id.in_(target_ids)).all():
            all_findings.setdefault(f.target_id, []).append(f)
        intel_map = {}
        for intel in session.query(TargetIntel).filter(TargetIntel.id.in_(target_ids)).all():
            intel_map[intel.id] = intel

        scored = []
        for t in targets:
            endpoints = all_endpoints.get(t.id, [])
            if not endpoints:
                continue
            findings = all_findings.get(t.id, [])
            intel = intel_map.get(t.id)

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

            payout = sum(SEVERITY_PAYOUT.get((f.severity or "info").lower(), 0) for f in findings)
            if intel and intel.reward_score:
                payout = int(payout * (1 + intel.reward_score / 100))
            roi = _target_roi(t, endpoints) / 10

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


def get_attack_surfaces() -> dict[str, list[dict[str, Any]]]:
    session = _get_session()
    try:
        endpoints = session.query(models.Endpoint).all()
        groups = {}
        _score_cache: dict[tuple[str, str], dict[str, Any]] = {}
        for ep in endpoints:
            cache_key = (ep.path or "/", ep.method or "GET")
            if cache_key not in _score_cache:
                _score_cache[cache_key] = _score_endpoint(ep)
            s = _score_cache[cache_key]
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


def get_pipeline_stages() -> dict[str, list[dict[str, Any]]]:
    session = _get_session()
    try:
        stages = {"detected": [], "validated": [], "confirmed": [], "reported": []}
        endpoints = session.query(models.Endpoint).all()
        findings = session.query(models.Finding).all()
        verdicts = session.query(models.Verdict).all()

        # Batch-load targets
        target_ids = list({f.target_id for f in findings})
        targets_map = {}
        for t in session.query(models.Target).filter(models.Target.id.in_(target_ids)).all():
            targets_map[t.id] = t

        # Batch-load TargetIntel for payout multipliers
        intel_map = {}
        for intel in session.query(TargetIntel).filter(TargetIntel.id.in_(target_ids)).all():
            intel_map[intel.id] = intel

        endpoint_map = {e.id: e for e in endpoints}
        endpoint_verdicts = {}
        for v in verdicts:
            if v.endpoint_id:
                endpoint_verdicts.setdefault(v.endpoint_id, []).append(v)

        for f in findings:
            target = targets_map.get(f.target_id)
            intel = intel_map.get(f.target_id)
            base_payout = SEVERITY_PAYOUT.get((f.severity or "info").lower(), 0)
            payout = int(base_payout * (1 + intel.reward_score / 100)) if intel and intel.reward_score else base_payout
            item = {
                "id": f.id,
                "target_id": f.target_id,
                "endpoint_id": f.endpoint_id,
                "title": f.title or f"Finding #{f.id}",
                "severity": f.severity or "medium",
                "description": f.description,
                "payout": payout,
                "target_name": target.name or f"#{target.id}" if target else "",
                "endpoint_path": "",
            }
            if f.endpoint_id:
                ep = endpoint_map.get(f.endpoint_id)
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


def generate_report() -> dict[str, Any]:
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

        # Batch-load TargetIntel for payout multipliers
        target_ids = list({f.target_id for f in findings})
        intel_map = {}
        if target_ids:
            for intel in session.query(TargetIntel).filter(TargetIntel.id.in_(target_ids)).all():
                intel_map[intel.id] = intel

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
            base_payout = SEVERITY_PAYOUT.get((f.severity or "info").lower(), 0)
            intel = intel_map.get(f.target_id)
            payout = int(base_payout * (1 + intel.reward_score / 100)) if intel and intel.reward_score else base_payout
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


# ── Create operations ───────────────────────────────

def create_target(name: str, domain: str | None = None) -> dict[str, Any]:
    session = _get_session()
    try:
        db_target = models.Target(name=name, domain=domain)
        session.add(db_target)
        session.commit()
        session.refresh(db_target)
        return {
            "id": db_target.id,
            "name": db_target.name,
            "domain": db_target.domain,
        }
    finally:
        session.close()


def create_endpoint(target_id: int, path: str, method: str = "GET", params: dict[str, Any] | None = None) -> dict[str, Any]:
    session = _get_session()
    try:
        target = session.query(models.Target).filter(models.Target.id == target_id).first()
        if not target:
            raise ValueError(f"Target {target_id} not found")
        db_endpoint = models.Endpoint(
            target_id=target_id,
            path=path,
            method=method,
            params=str(params) if params else None,
        )
        session.add(db_endpoint)
        session.commit()
        session.refresh(db_endpoint)
        return {
            "id": db_endpoint.id,
            "target_id": db_endpoint.target_id,
            "path": db_endpoint.path,
            "method": db_endpoint.method,
        }
    finally:
        session.close()


def create_finding(target_id: int, title: str, severity: str = "medium", description: str | None = None, endpoint_id: int | None = None) -> dict[str, Any]:
    session = _get_session()
    try:
        target = session.query(models.Target).filter(models.Target.id == target_id).first()
        if not target:
            raise ValueError(f"Target {target_id} not found")
        if endpoint_id:
            endpoint = session.query(models.Endpoint).filter(models.Endpoint.id == endpoint_id).first()
            if not endpoint:
                raise ValueError(f"Endpoint {endpoint_id} not found")
        db_finding = models.Finding(
            target_id=target_id,
            endpoint_id=endpoint_id,
            title=title,
            severity=severity,
            description=description,
        )
        session.add(db_finding)
        session.commit()
        session.refresh(db_finding)
        return {
            "id": db_finding.id,
            "title": db_finding.title,
            "severity": db_finding.severity,
        }
    finally:
        session.close()


# ── Scan / Digest ──────────────────────────────────

def list_scan_runs(target_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    session = _get_session()
    try:
        q = session.query(models.ScanRun)
        if target_id:
            q = q.filter(models.ScanRun.target_id == target_id)
        runs = q.order_by(models.ScanRun.started_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "target_id": r.target_id,
                "mode": r.mode,
                "status": r.status,
                "endpoint_count": r.endpoint_count,
                "started_at": r.started_at.isoformat(sep=" ", timespec="seconds") if r.started_at else None,
                "finished_at": r.finished_at.isoformat(sep=" ", timespec="seconds") if r.finished_at else None,
            }
            for r in runs
        ]
    finally:
        session.close()


def get_scan_run(scan_id: int) -> dict[str, Any] | None:
    session = _get_session()
    try:
        r = session.query(models.ScanRun).filter(models.ScanRun.id == scan_id).first()
        if not r:
            return None
        return {
            "id": r.id,
            "target_id": r.target_id,
            "mode": r.mode,
            "status": r.status,
            "endpoint_count": r.endpoint_count,
            "outputs": r.outputs,
            "started_at": r.started_at.isoformat(sep=" ", timespec="seconds") if r.started_at else None,
            "finished_at": r.finished_at.isoformat(sep=" ", timespec="seconds") if r.finished_at else None,
        }
    finally:
        session.close()


def get_digest() -> dict[str, Any]:
    session = _get_session()
    try:
        entries = []
        endpoints = session.query(models.Endpoint).all()
        _score_cache: dict[str, dict[str, Any]] = {}
        for ep in endpoints:
            safe_path = str(ep.path or "/")
            safe_method = str(ep.method or "GET")
            cache_key = f"{safe_method}:{safe_path}"
            if cache_key not in _score_cache:
                _score_cache[cache_key] = unified_score(safe_path, safe_method, ep.parsed_params)
            result = _score_cache[cache_key]
            entries.append({
                "id": ep.id,
                "target_id": ep.target_id,
                "path": safe_path,
                "method": safe_method,
                "labels": result["labels"],
                "risk_score": result["risk_score"],
            })
        entries.sort(key=lambda item: item["risk_score"], reverse=True)

        high_signal = [e for e in entries if e["risk_score"] >= 0.5]
        total_endpoints = len(endpoints)
        pending_review = session.query(models.Verdict).filter(models.Verdict.status == "pending").count()
        new_opportunities = 0
        summary_lines = []
        if high_signal:
            summary_lines.append(f"{len(high_signal)} endpoints with high risk score")
        if pending_review:
            summary_lines.append(f"{pending_review} verdicts pending review")
        if new_opportunities:
            summary_lines.append(f"{new_opportunities} opportunities identified")
        summary = "; ".join(summary_lines) if summary_lines else "All clear — no issues detected"

        return {
            "high_signal_findings": len(high_signal),
            "total_endpoints_scanned": total_endpoints,
            "pending_review": pending_review,
            "new_opportunities": new_opportunities,
            "summary": summary,
            "high_signal": high_signal[:20],
        }
    finally:
        session.close()


# ── Verdicts ───────────────────────────────────────

def list_verdicts(status: str | None = None, confidence_min: float = 0.0, target_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
    session = _get_session()
    try:
        from sqlalchemy import Float, cast
        q = session.query(models.Verdict)
        if status:
            q = q.filter(models.Verdict.status == status)
        if confidence_min > 0:
            q = q.filter(cast(models.Verdict.confidence, Float) >= confidence_min)
        if target_id:
            q = q.filter(models.Verdict.endpoint_id.in_(
                session.query(models.Endpoint.id).filter(models.Endpoint.target_id == target_id)
            ))
        verdicts = q.order_by(models.Verdict.created_at.desc()).limit(limit).all()
        return [
            {
                "id": v.id,
                "hot_path_id": v.hot_path_id,
                "status": v.status,
                "confidence": _parse_confidence(v.confidence),
                "reproducibility_score": float(v.reproducibility_score) if v.reproducibility_score else 0.0,
                "retry_count": v.retry_count,
                "reason": v.reason,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "validation_report": __import__("json").loads(v.validation_report) if v.validation_report else {},
            }
            for v in verdicts
        ]
    finally:
        session.close()


def _parse_confidence(raw) -> float:
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        raw_stripped = raw.strip()
        if raw_stripped.startswith("{"):
            try:
                return float(__import__("json").loads(raw_stripped).get("score", 0.0))
            except (ValueError, TypeError, __import__("json").JSONDecodeError):
                pass
        try:
            return float(raw_stripped)
        except (ValueError, TypeError):
            pass
    return 0.0


def get_verdict(verdict_id: int) -> dict[str, Any] | None:
    session = _get_session()
    try:
        v = session.query(models.Verdict).filter(models.Verdict.id == verdict_id).first()
        if not v:
            return None
        return {
            "id": v.id,
            "hot_path_id": v.hot_path_id,
            "status": v.status,
            "confidence": _parse_confidence(v.confidence),
            "reproducibility_score": float(v.reproducibility_score) if v.reproducibility_score else 0.0,
            "retry_count": v.retry_count,
            "reason": v.reason,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "validation_report": __import__("json").loads(v.validation_report) if v.validation_report else {},
            "confidence_details": __import__("json").loads(v.confidence_details) if v.confidence_details else {},
        }
    finally:
        session.close()


def get_evidence_for_verdict(verdict_id: int) -> dict[str, Any]:
    session = _get_session()
    try:
        evidence_records = session.query(models.Evidence).filter(
            models.Evidence.verdict_id == verdict_id
        ).order_by(models.Evidence.id).all()
        attempts = []
        for ev in evidence_records:
            attempts.append({
                "attempt": ev.attempt_label,
                "status_code": ev.response_status,
                "consistent": ev.consistent == "true",
                "body_diff_ratio": float(ev.body_diff_ratio) if ev.body_diff_ratio else 0.0,
                "sensitive_fields": __import__("json").loads(ev.sensitive_fields) if ev.sensitive_fields else [],
                "curl_command": ev.curl_command,
                "body_hash": ev.response_body_hash,
            })
        return {
            "verdict_id": verdict_id,
            "total_attempts": len(evidence_records),
            "attempts": attempts,
            "summary": {
                "total_attempts": len(evidence_records),
                "consistent_count": sum(1 for ev in evidence_records if ev.consistent == "true"),
                "consistency_ratio": sum(1 for ev in evidence_records if ev.consistent == "true") / max(len(evidence_records), 1),
            },
            "reproduction_steps": [
                "1. Obtain authentication tokens for two different users",
                "2. Execute the curl commands below as each user",
                "3. Compare responses for sensitive data leakage",
                "4. Verify consistent access across different privilege levels",
            ],
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
