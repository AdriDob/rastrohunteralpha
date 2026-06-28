"""
Screenshot Engine API — expose visual evidence representations.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core_engines.engine.snapshot import (
    EndpointSnapshot,
    PipelineSnapshot,
    TargetSnapshot,
)
from core_engines.engine.unified_scoring import score as unified_score
from core_engines.screenshot.engine import ScreenshotEngine
from database import db, models

router = APIRouter(prefix="/api/screenshots", tags=["screenshots"])


@router.get("")
def get_screenshots(target_id: int | None = None):
    session = db.SessionLocal()
    try:
        targets = session.query(models.Target).all()
        if target_id is not None:
            targets = [t for t in targets if t.id == target_id]
            if not targets:
                raise HTTPException(status_code=404, detail=f"Target {target_id} not found")

        if not targets:
            return {"specs": [], "summary": "No targets available", "key_risks": [], "roi_highlights": []}

        first_target = targets[0]
        endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == first_target.id).all()

        ep_snapshots = []
        for ep in endpoints:
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

        target_snapshot = TargetSnapshot(
            target_id=first_target.id,
            name=first_target.name or f"Target #{first_target.id}",
            domain=first_target.domain,
            endpoint_count=len(endpoints),
            risk_score=float(max((ep.risk_score for ep in ep_snapshots), default=0)),
        )

        from datetime import datetime, timezone

        snapshot = PipelineSnapshot(
            status="completed",
            target=target_snapshot,
            endpoints=ep_snapshots,
            hot_paths=[],
            verdicts=[],
            reports=[],
            coverage_score=0.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        engine = ScreenshotEngine()
        bundle = engine.build(
            snapshot=snapshot,
            target_name=first_target.name or "",
        )

        return {
            "specs": [
                {
                    "title": s.title,
                    "target": s.target,
                    "endpoint": s.endpoint,
                    "vulnerability_type": s.vulnerability_type,
                    "severity": s.severity,
                    "roi_score": s.roi_score,
                    "visual_blocks": [
                        {"type": b.type, "content": b.content, "highlight_level": b.highlight_level}
                        for b in s.visual_blocks
                    ],
                    "annotations": [
                        {"category": a.category, "detail": a.detail, "severity": a.severity}
                        for a in s.annotations
                    ],
                    "before_state": s.before_state,
                    "after_state": s.after_state,
                    "attack_path_summary": s.attack_path_summary,
                    "confidence": s.confidence,
                }
                for s in bundle.specs
            ],
            "summary": bundle.summary,
            "key_risks": bundle.key_risks,
            "roi_highlights": bundle.roi_highlights,
        }
    finally:
        session.close()
