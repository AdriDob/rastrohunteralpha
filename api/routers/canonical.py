"""
api.routers.canonical — Canonical API endpoints that return official Bundles.

All endpoints consume from the intelligence layer and return artifacts.
No business logic — pure presentation of canonical data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core_engines.intelligence.unified_orchestrator import get_orchestrator

LOG = logging.getLogger("rastro.api.canonical")

router = APIRouter(prefix="/api", tags=["canonical"])


def _get_artifact(name: str):
    orch = get_orchestrator()
    artifact = orch.get(name)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"{name} not available. Run a pipeline first.")
    return artifact


@router.get("/pipeline")
async def get_pipeline():
    """Return the canonical PipelineArtifact."""
    return _get_artifact("PipelineArtifact")


@router.get("/evidence")
async def get_evidence():
    """Return the canonical EvidenceGraphArtifact."""
    return _get_artifact("EvidenceGraphArtifact")


@router.get("/quickwins")
async def get_quick_wins():
    """Return the canonical QuickWinsArtifact."""
    return _get_artifact("QuickWinsArtifact")


@router.get("/screenshots")
async def get_screenshots():
    """Return the canonical ScreenshotArtifact."""
    return _get_artifact("ScreenshotArtifact")


@router.get("/differential")
async def get_differential():
    """Return the canonical DifferentialArtifact."""
    return _get_artifact("DifferentialArtifact")


@router.get("/insights")
async def get_insights():
    """Return the canonical AIInsightArtifact."""
    return _get_artifact("AIInsightArtifact")


@router.get("/execution")
async def get_execution():
    """Return the canonical ExecutionPlanArtifact."""
    return _get_artifact("ExecutionPlanArtifact")


@router.get("/attack-surface")
async def get_attack_surface():
    """Return the canonical AttackSurfaceArtifact."""
    return _get_artifact("AttackSurfaceArtifact")


@router.get("/roi")
async def get_roi():
    """Return the canonical ROIArtifact."""
    return _get_artifact("ROIArtifact")


@router.get("/hypotheses")
async def get_hypotheses():
    """Return the canonical HypothesisArtifact."""
    return _get_artifact("HypothesisArtifact")


@router.get("/artifacts")
async def list_artifacts():
    """List all available artifacts and their status."""
    orch = get_orchestrator()
    stats = orch.stats()
    return {
        "available": stats.get("artifacts_available", []),
        "execution_order": stats.get("dependency_graph", {}).get("execution_order", []),
        "metrics": stats.get("metrics", {}),
    }


@router.get("/events")
async def get_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
):
    """Get the event history."""
    from core_engines.intelligence.event_system import get_event_system
    es = get_event_system()
    return {"events": es.get_events(event_type)}


@router.get("/metrics")
async def get_metrics():
    """Get system-wide observability metrics."""
    orch = get_orchestrator()
    return {"metrics": orch.stats().get("metrics", {})}


@router.get("/anti-drift")
async def get_anti_drift_report():
    """Get anti-drift violation report."""
    from core_engines.intelligence.anti_drift import get_enforcer
    enforcer = get_enforcer()
    return enforcer.report()
