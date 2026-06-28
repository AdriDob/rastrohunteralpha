"""
Differential Intelligence API — expose interesting differences and anomalies.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core_engines.differential_intelligence import DifferentialIntelligenceEngine
from core_engines.engine.snapshot import (
    AttackSurfaceSnapshot,
    EndpointSnapshot,
    PipelineSnapshot,
    TargetSnapshot,
)
from core_engines.engine.unified_scoring import score as unified_score
from core_engines.evidence.graph import EvidenceGraph
from database import db, models

router = APIRouter(prefix="/api/differential-intelligence", tags=["differential_intelligence"])


def _build_snapshot(target_id: int | None = None) -> PipelineSnapshot:
    """Build a PipelineSnapshot from database for differential analysis."""
    session = db.SessionLocal()
    try:
        targets = session.query(models.Target).all()
        if target_id is not None:
            targets = [t for t in targets if t.id == target_id]
            if not targets:
                raise HTTPException(status_code=404, detail=f"Target {target_id} not found")

        if not targets:
            raise HTTPException(status_code=404, detail="No targets found")

        endpoints = session.query(models.Endpoint).all()
        first_target = targets[0]
        target_eps = [ep for ep in endpoints if ep.target_id == first_target.id] if first_target else []

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

        from datetime import datetime, timezone

        target_snapshot = None
        if first_target:
            target_snapshot = TargetSnapshot(
                target_id=first_target.id,
                name=first_target.name or f"Target #{first_target.id}",
                domain=first_target.domain,
                endpoint_count=len(target_eps),
                risk_score=float(max((ep.risk_score for ep in ep_snapshots), default=0)),
            )

        # Build attack surface snapshot from available data
        idor_clusters = []
        auth_boundaries = []
        multi_tenant_zones = []
        graphql_surfaces = []
        for ep in ep_snapshots:
            if ep.potential_idor or "idor_candidate" in ep.attack_surface:
                idor_clusters.append({"path": ep.path, "method": ep.method, "risk_score": ep.risk_score})
            if "authentication_surface" in ep.attack_surface:
                auth_boundaries.append({"path": ep.path, "method": ep.method, "risk_score": ep.risk_score})
            if "tenant_boundary" in ep.attack_surface:
                multi_tenant_zones.append({"path": ep.path, "method": ep.method, "risk_score": ep.risk_score})
            if "graphql" in ep.labels:
                graphql_surfaces.append({"path": ep.path, "method": ep.method, "risk_score": ep.risk_score})

        return PipelineSnapshot(
            status="completed",
            target=target_snapshot,
            endpoints=ep_snapshots,
            hot_paths=[],
            verdicts=[],
            reports=[],
            attack_surface=AttackSurfaceSnapshot(
                idor_clusters=idor_clusters,
                auth_boundaries=auth_boundaries,
                multi_tenant_zones=multi_tenant_zones,
                graphql_surfaces=graphql_surfaces,
            ),
            coverage_score=0.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary=f"Differential intelligence analysis for {first_target.name}",
        )
    finally:
        session.close()


def _finding_to_dict(f) -> dict[str, Any]:
    return {
        "title": f.title,
        "category": f.category,
        "description": f.description,
        "affected_objects": f.affected_objects,
        "confidence": f.confidence,
        "supporting_signals": f.supporting_signals,
        "risk_level": f.risk_level,
        "requires_validation": f.requires_validation,
        "novelty_score": f.novelty_score,
        "confidence_score": f.confidence_score,
        "potential_roi": f.potential_roi,
        "validation_priority": f.validation_priority,
    }


def _bundle_to_dict(bundle) -> dict[str, Any]:
    return {
        "target_differences": [_finding_to_dict(f) for f in bundle.target_differences],
        "endpoint_differences": [_finding_to_dict(f) for f in bundle.endpoint_differences],
        "historical_changes": [_finding_to_dict(f) for f in bundle.historical_changes],
        "cross_target_patterns": [_finding_to_dict(f) for f in bundle.cross_target_patterns],
        "web3_differences": [_finding_to_dict(f) for f in bundle.web3_differences],
        "interesting_anomalies": [_finding_to_dict(f) for f in bundle.interesting_anomalies],
        "confidence": bundle.confidence,
        "summary": bundle.summary,
    }


@router.get("/analyze")
def analyze_target(target_id: int | None = None):
    """Run differential intelligence analysis for a target."""
    snapshot = _build_snapshot(target_id)
    evidence_graph = EvidenceGraph()
    engine = DifferentialIntelligenceEngine()
    bundle = engine.analyze(
        snapshot=snapshot,
        evidence_graph=evidence_graph,
    )
    return _bundle_to_dict(bundle)


@router.get("/analyze/endpoints")
def analyze_endpoints(target_id: int | None = None):
    """Analyze endpoint-level differences for a target."""
    snapshot = _build_snapshot(target_id)
    evidence_graph = EvidenceGraph()
    engine = DifferentialIntelligenceEngine()
    bundle = engine.analyze(
        snapshot=snapshot,
        evidence_graph=evidence_graph,
    )
    return {
        "endpoint_differences": [_finding_to_dict(f) for f in bundle.endpoint_differences],
        "interesting_anomalies": [_finding_to_dict(f) for f in bundle.interesting_anomalies],
        "summary": bundle.summary,
    }


@router.get("/analyze/web3")
def analyze_web3(target_id: int | None = None):
    """Analyze Web3-specific differences for a target."""
    snapshot = _build_snapshot(target_id)
    evidence_graph = EvidenceGraph()
    engine = DifferentialIntelligenceEngine()
    bundle = engine.analyze(
        snapshot=snapshot,
        evidence_graph=evidence_graph,
    )
    return {
        "web3_differences": [_finding_to_dict(f) for f in bundle.web3_differences],
        "summary": f"Web3: {bundle.summary}",
    }
