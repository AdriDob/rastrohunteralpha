from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas.models import HypothesisEngineOutputOut, HypothesisOut
from api.services.data_service import _get_session, _score_endpoint
from database import models
from core.engine.hypothesis import HypothesisEngine

router = APIRouter(prefix="/api/hypotheses", tags=["hypotheses"])


def _hypothesis_to_out(h: Any) -> Dict[str, Any]:
    return {
        "id": h.id,
        "vulnerability_type": h.vulnerability_type.value,
        "target_id": h.target_id,
        "target_name": h.target_name,
        "endpoint": h.endpoint,
        "likelihood": h.likelihood,
        "impact": h.impact,
        "exploitability": h.exploitability,
        "confidence": h.confidence,
        "priority_score": h.priority_score,
        "roi_score": h.roi_score,
        "evidence": h.evidence,
        "reasoning": h.reasoning,
        "suggested_actions": h.suggested_actions,
        "source": h.source.value,
        "vector": h.vector,
        "attack_surface_labels": h.attack_surface_labels,
        "similarity_to_past": h.similarity_to_past,
        "past_pattern_id": h.past_pattern_id,
        "score": {
            "likelihood": h.score.likelihood,
            "impact": h.score.impact,
            "exploitability": h.score.exploitability,
            "confidence": h.score.confidence,
            "priority_score": h.score.priority_score,
            "breakdown": {
                **h.score.breakdown,
                "roi_score": h.roi_score,
            },
        },
    }


@router.post("/{target_id}", response_model=HypothesisEngineOutputOut)
def run_hypotheses(target_id: int):
    """Run the Hypothesis Engine against a target — generates, scores, and prioritizes hypotheses."""
    session = _get_session()
    try:
        target = session.query(models.Target).filter(models.Target.id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")

        endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == target_id).all()
        if not endpoints:
            raise HTTPException(status_code=400, detail="Target has no endpoints to analyze")

        scored_endpoints = []
        for ep in endpoints:
            s = _score_endpoint(ep)
            scored_endpoints.append({
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
                "parsed_params": ep.parsed_params,
            })

        engine = HypothesisEngine()
        output = engine.run(
            target_id=target.id,
            target_name=target.name or f"Target #{target.id}",
            endpoints=scored_endpoints,
        )

        return {
            "attack_queue": [_hypothesis_to_out(h) for h in output.attack_queue.prioritized()],
            "total_hypotheses": output.total_hypotheses,
            "by_source": output.by_source,
            "by_type": output.by_type,
            "top_priority": _hypothesis_to_out(output.top_priority) if output.top_priority else None,
            "summary": output.summary,
            "total_roi_value": output.total_roi_value,
            "avg_roi": output.avg_roi,
            "max_roi": output.max_roi,
            "profitable_count": output.profitable_count,
        }
    finally:
        session.close()
