from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from api.schemas.models import TargetROIOut
from api.services.data_service import _get_session, _score_endpoint
from core_engines.engine.hypothesis import HypothesisEngine
from database import models

router = APIRouter(prefix="/api/roi", tags=["roi"])


def _build_roi_detail(
    hypothesis: Any,
    endpoint_path: str = "",
    endpoint_method: str = "GET",
) -> dict[str, Any]:
    score = hypothesis.score
    breakdown = dict(score.breakdown) if hasattr(score, "breakdown") else {}
    return {
        "endpoint_id": hypothesis.endpoint.get("id") if hypothesis.endpoint else None,
        "hypothesis_id": hypothesis.id,
        "vulnerability_type": hypothesis.vulnerability_type.value if hasattr(hypothesis.vulnerability_type, "value") else str(hypothesis.vulnerability_type),
        "path": endpoint_path or hypothesis.endpoint.get("path", ""),
        "method": endpoint_method or hypothesis.endpoint.get("method", "GET"),
        "roi_normalized": hypothesis.roi_score,
        "roi_ratio": breakdown.get("roi_ratio", 0.0),
        "payout_estimate": breakdown.get("payout_estimate", 0.0),
        "time_cost_hours": breakdown.get("time_cost_hours", 0.0),
        "expected_return": breakdown.get("expected_return", 0.0),
        "expected_cost": breakdown.get("expected_cost", 0.0),
        "probability_success": breakdown.get("probability_success", 0.0),
        "priority_score": hypothesis.priority_score,
        "is_profitable": hypothesis.roi_score > 50.0,
        "breakdown": breakdown,
    }


@router.get("/{target_id}", response_model=TargetROIOut)
def get_target_roi(target_id: int):
    """Compute and return full ROI analysis for a target."""
    session = _get_session()
    try:
        target = session.query(models.Target).filter(models.Target.id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")

        endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == target_id).all()
        if not endpoints:
            raise HTTPException(status_code=400, detail="Target has no endpoints")

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

        prioritized = output.attack_queue.prioritized()
        roi_details = []
        ep_map = {ep.get("id"): ep for ep in scored_endpoints}

        for h in prioritized:
            ep = ep_map.get(h.endpoint.get("id")) if h.endpoint else None
            roi_details.append(_build_roi_detail(
                h,
                endpoint_path=ep.get("path", "") if ep else "",
                endpoint_method=ep.get("method", "GET") if ep else "GET",
            ))

        [r for r in roi_details if r["is_profitable"]]
        total_return = sum(r["expected_return"] for r in roi_details)
        total_cost = sum(r["expected_cost"] for r in roi_details)
        highest_payout = max((r["payout_estimate"] for r in roi_details), default=0.0)

        return {
            "target_id": target.id,
            "target_name": target.name or f"Target #{target.id}",
            "total_hypotheses": output.total_hypotheses,
            "avg_roi": output.avg_roi,
            "max_roi": output.max_roi,
            "profitable_count": output.profitable_count,
            "total_expected_return": round(total_return, 2),
            "total_expected_cost": round(total_cost, 2),
            "highest_payout": highest_payout,
            "top_opportunities": roi_details[:10],
            "all_roi": roi_details,
        }
    finally:
        session.close()
