"""
Quick Wins API — evaluate monetization opportunities from pipeline data.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, HTTPException

from core_engines.engine.snapshot import (
    EndpointSnapshot,
    HotPathSnapshot,
    PipelineSnapshot,
    ReportSnapshot,
    TargetSnapshot,
    VerdictSnapshot,
)
from core_engines.evidence.graph import EvidenceGraph
from core_engines.quick_wins.quick_wins_engine import QuickWinsEngine
from core_engines.engine.unified_scoring import score as unified_score
from database import db, models

router = APIRouter(prefix="/api/quick-wins", tags=["quick_wins"])


def _build_snapshot(target_id: Optional[int] = None) -> PipelineSnapshot:
    session = db.SessionLocal()
    try:
        targets = session.query(models.Target).all()
        if target_id is not None:
            targets = [t for t in targets if t.id == target_id]
            if not targets:
                raise HTTPException(status_code=404, detail=f"Target {target_id} not found")

        endpoints = session.query(models.Endpoint).all()
        verdicts = session.query(models.Verdict).all()
        findings = session.query(models.Finding).all()

        first_target = targets[0] if targets else None
        target_eps = [ep for ep in endpoints if ep.target_id == first_target.id] if first_target else []
        target_findings = [f for f in findings if f.target_id == first_target.id] if first_target else []
        target_verdicts = [v for v in verdicts if v.endpoint_id and v.endpoint_id in {ep.id for ep in target_eps}] if first_target else []

        ep_snapshots = []
        for ep in target_eps:
            s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
            ep_snapshots.append(EndpointSnapshot(
                path=ep.path,
                method=ep.method or "GET",
                risk_score=float(s.get("risk_score", 0)),
                confidence=float(s.get("confidence", 0)),
                labels=s.get("labels", []),
                attack_surface=s.get("attack_surface", []),
                signals=s.get("signals", []),
                vector=s.get("vector", ""),
                actionable=bool(s.get("actionable", False)),
                potential_idor=bool(s.get("potential_idor", False)),
            ))

        def _parse_confidence(raw) -> float:
            if isinstance(raw, (int, float)):
                return float(raw)
            if isinstance(raw, str):
                try:
                    import json
                    return float(json.loads(raw).get("score", 0))
                except (json.JSONDecodeError, TypeError, ValueError):
                    try:
                        return float(raw)
                    except (ValueError, TypeError):
                        return 0.0
            return 0.0

        hot_path_snapshots = [
            HotPathSnapshot(
                node_id=v.hot_path_id or f"v:{v.id}",
                path="",
                method="",
                risk_score=_parse_confidence(v.confidence) * 100,
                vector="",
            )
            for v in target_verdicts
        ]

        verdict_snapshots = [
            VerdictSnapshot(
                hot_path_id=v.hot_path_id or f"v:{v.id}",
                status=v.status or "unknown",
                confidence=_parse_confidence(v.confidence),
                reproducibility_score=float(v.reproducibility_score or 0),
            )
            for v in target_verdicts
        ]

        report_snapshots = [
            ReportSnapshot(
                title=f.title or f"Finding #{f.id}",
                severity=f.severity or "medium",
                affected_endpoint=str(f.endpoint_id or ""),
                attack_vector="",
            )
            for f in target_findings
        ]

        target_snapshot = None
        if first_target:
            target_snapshot = TargetSnapshot(
                target_id=first_target.id,
                name=first_target.name or f"Target #{first_target.id}",
                domain=first_target.domain,
                endpoint_count=len(target_eps),
                risk_score=float(max((ep.risk_score for ep in ep_snapshots), default=0)),
            )

        from datetime import datetime, timezone

        return PipelineSnapshot(
            status="completed",
            target=target_snapshot,
            endpoints=ep_snapshots,
            hot_paths=hot_path_snapshots,
            verdicts=verdict_snapshots,
            reports=report_snapshots,
            coverage_score=0.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        session.close()


@router.post("/evaluate")
def evaluate_quick_wins(target_id: Optional[int] = None):
    snapshot = _build_snapshot(target_id)
    evidence_graph = EvidenceGraph()
    engine = QuickWinsEngine()
    report = engine.evaluate(snapshot, evidence_graph)
    return {"report": asdict(report), "snapshot_status": snapshot.status}
