"""
Rastro Opportunity Intelligence Layer — /api/opportunity/

All endpoints are read-only. Never modifies pipeline data.
Supports advanced layered scoring, EVH rankings, identity vault.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from core.opportunity import get_engine
from core.identity_vault import get_identity_vault

logger = logging.getLogger("rastro.opportunity.api")

router = APIRouter(prefix="/api/opportunity", tags=["opportunity"])

_EXPORT_FIELDS = [
    "name", "category", "priority", "score", "source_type", "source_name",
    "public_url", "scope_summary", "reward_info", "technology_tags",
    "confidence", "reasoning", "evh", "has_rewards",
]


def _format_opps(opps: List[Any], fmt: str = "json") -> Any:
    """Format opportunity list as JSON, CSV, or Markdown."""
    if fmt == "json":
        return {"opportunities": [_opp_to_dict(o) for o in opps], "count": len(opps)}

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(_EXPORT_FIELDS)
        for o in opps:
            d = _opp_to_dict(o)
            writer.writerow([
                d.get("name", ""), d.get("category", ""), d.get("priority", ""),
                d.get("score", ""), d.get("source_type", ""), d.get("source_name", ""),
                d.get("public_url", ""), d.get("scope_summary", ""), d.get("reward_info", ""),
                ", ".join(d.get("technology_tags", [])), d.get("confidence", ""),
                "; ".join(d.get("reasoning", [])),
                str(d.get("evh", {}).get("value", "")),
                d.get("has_rewards", True),
            ])
        return PlainTextResponse(output.getvalue(), media_type="text/csv")

    if fmt == "markdown":
        lines = ["| Name | Category | Priority | Score | EVH | Source | Rewards |",
                 "|------|----------|----------|-------|-----|--------|---------|"]
        for o in opps:
            d = _opp_to_dict(o)
            evh_val = d.get("evh", {}).get("value", "")
            evh_label = d.get("evh", {}).get("rating", "")
            rewards = "✓" if d.get("has_rewards", True) else "✗"
            lines.append(
                f"| {d.get('name', '')} | {d.get('category', '')} | {d.get('priority', '')} "
                f"| {d.get('score', '')} | ${evh_val}/hr ({evh_label}) "
                f"| {d.get('source_name', '')} | {rewards} |"
            )
        return PlainTextResponse("\n".join(lines), media_type="text/markdown")

    return {"opportunities": [], "count": 0}


def _opp_to_dict(opp: Any) -> Dict[str, Any]:
    score = opp.score
    evh_data = {}
    if score and score.evh:
        evh_data = {
            "value": score.evh.value,
            "rating": score.evh.rating,
            "estimated_payout": score.evh.estimated_payout,
            "success_probability": score.evh.success_probability,
            "estimated_effort_hours": score.evh.estimated_effort_hours,
            "explanation": score.evh.explanation,
        }

    breakdown_data = None
    if score and score.breakdown:
        b = score.breakdown
        breakdown_data = {
            "reward_score": b.reward_score,
            "reward_explanation": b.reward_explanation,
            "competition_score": b.competition_score,
            "competition_explanation": b.competition_explanation,
            "discovery_score": b.discovery_score,
            "discovery_explanation": b.discovery_explanation,
            "execution_score": b.execution_score,
            "execution_explanation": b.execution_explanation,
            "intelligence_score": b.intelligence_score,
            "intelligence_explanation": b.intelligence_explanation,
            "strategic_score": b.strategic_score,
            "strategic_explanation": b.strategic_explanation,
            "confidence_score": b.confidence_score,
            "confidence_explanation": b.confidence_explanation,
        }

    return {
        "id": opp.id,
        "name": opp.name,
        "category": opp.category,
        "subcategory": opp.subcategory or "",
        "priority": opp.priority or "unknown",
        "score": round(score.overall, 4) if score else 0.0,
        "source_type": opp.source.type,
        "source_name": opp.source.name,
        "public_url": opp.public_url or "",
        "scope_summary": opp.scope_summary or "",
        "reward_info": opp.reward_info or "",
        "technology_tags": list(opp.technology_tags),
        "confidence": opp.confidence,
        "reasoning": list(score.reasoning) if score else [],
        "created_at": opp.created_at or "",
        "last_update": opp.last_update or "",
        "has_rewards": opp.has_rewards,
        "estimated_payout": opp.estimated_payout,
        "estimated_effort_hours": opp.estimated_effort_hours,
        "evh": evh_data,
        "score_breakdown": breakdown_data,
    }


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/refresh")
def refresh_opportunities():
    """Run discovery on all providers and re-score everything."""
    engine = get_engine()
    try:
        engine.discover_all(use_layered_scoring=True)
        engine.take_snapshot("daily")
        return {"status": "ok", "count": len(engine.get_all()), "refreshed_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/overview")
def opportunity_overview():
    """High-level metrics and breakdown with EVH and provider health."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    return {
        "metrics": engine.get_metrics(),
        "providers": [
            {"name": p.name, "category": p.category, "opportunity_count": p.opportunity_count,
             "health_status": p.health_status, "last_refresh": p.last_refresh}
            for p in engine.get_providers_info()
        ],
        "recommendations_summary": engine.get_recommendations().summary,
        "last_refresh": engine.get_metrics().get("last_refresh", ""),
    }


@router.get("/top")
def top_opportunities(
    limit: int = Query(20, ge=1, le=100),
    fmt: str = Query("json", pattern="^(json|csv|markdown)$"),
):
    """Top-scored opportunities across all categories."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    return _format_opps(engine.get_all()[:limit], fmt)


@router.get("/recommendations")
def get_recommendations():
    """Generated advisory recommendations with EVH rankings."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    recs = engine.get_recommendations()
    return {
        "top_opportunities": [_opp_to_dict(o) for o in recs.top_opportunities],
        "top_independent": [_opp_to_dict(o) for o in recs.top_independent],
        "top_web3": [_opp_to_dict(o) for o in recs.top_web3],
        "fast_roi": [_opp_to_dict(o) for o in recs.fast_roi],
        "long_term": [_opp_to_dict(o) for o in recs.long_term],
        "low_competition": [_opp_to_dict(o) for o in recs.low_competition],
        "evh_ranked": [_opp_to_dict(o) for o in recs.evh_ranked],
        "summary": recs.summary,
        "generated_at": recs.generated_at,
    }


@router.get("/evh")
def evh_rankings(limit: int = Query(20, ge=1, le=100)):
    """Opportunities ranked by Expected Value Per Hour."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    ranked = engine.get_evh_rankings(limit)
    return {
        "rankings": [_opp_to_dict(o) for o in ranked],
        "summary": engine.get_evh_summary(),
        "count": len(ranked),
    }


@router.get("/score-breakdown/{opp_id}")
def score_breakdown(opp_id: str):
    """Detailed layered score breakdown for a specific opportunity."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    opp = engine.get_by_id(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return _opp_to_dict(opp)


@router.get("/categories")
def list_categories():
    """List all available opportunity categories with counts."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    all_opps = engine.get_all()
    categories: Dict[str, int] = {}
    for o in all_opps:
        categories[o.category] = categories.get(o.category, 0) + 1
    return {
        "categories": [{"name": k, "count": v} for k, v in sorted(categories.items())],
        "total": len(all_opps),
    }


# ── Identity Vault Endpoints ─────────────────────────────────────────

@router.get("/identity/accounts")
def list_identity_accounts():
    """List all stored provider identities (no secrets)."""
    vault = get_identity_vault()
    return {
        "accounts": vault.list_accounts(),
        "connected_count": vault.connected_count(),
    }


@router.post("/identity/store")
def store_identity(data: Dict[str, Any]):
    """Store encrypted credentials for a provider."""
    provider = data.get("provider", "")
    email = data.get("email", "")
    token = data.get("token", "")
    password = data.get("password", "")
    metadata = data.get("metadata")

    if not provider:
        raise HTTPException(status_code=400, detail="provider name required")
    if not email:
        raise HTTPException(status_code=400, detail="email required")

    vault = get_identity_vault()
    vault.store_credentials(provider, email, token, password, metadata)
    return {"status": "ok", "provider": provider, "email": email}


@router.post("/identity/remove/{provider}")
def remove_identity(provider: str):
    """Remove stored credentials for a provider."""
    vault = get_identity_vault()
    vault.remove_credentials(provider)
    return {"status": "ok", "provider": provider}


@router.get("/identity/status/{provider}")
def identity_status(provider: str):
    """Check session health for a provider identity."""
    vault = get_identity_vault()
    account = vault.get_account(provider)
    if not account:
        raise HTTPException(status_code=404, detail="No identity stored for provider")
    health = vault.check_session_health(provider)
    return {"provider": provider, "account": account, "session_health": health}


# ── Emerging / Category endpoints ────────────────────────────────────

@router.get("/emerging")
def emerging_opportunities(
    fmt: str = Query("json", pattern="^(json|csv|markdown)$"),
):
    """Tracked emerging / new public opportunities."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    emerging = [o for o in engine.get_all() if o.category in ("emerging", "research")]
    emerging.sort(key=lambda o: o.score.overall if o.score else 0, reverse=True)
    return _format_opps(emerging, fmt)


@router.get("/independent")
def independent_opportunities(fmt: str = Query("json", pattern="^(json|csv|markdown)$")):
    """Independent / self-run program opportunities."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    return _format_opps([o for o in engine.get_all() if o.category == "independent"], fmt)


@router.get("/web3")
def web3_opportunities(fmt: str = Query("json", pattern="^(json|csv|markdown)$")):
    """Web3-specific opportunities."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    return _format_opps([o for o in engine.get_all() if o.category == "web3"], fmt)


@router.get("/by-category/{category}")
def opportunities_by_category(
    category: str,
    fmt: str = Query("json", pattern="^(json|csv|markdown)$"),
):
    """Opportunities filtered by category."""
    engine = get_engine()
    if not engine.get_all():
        engine.discover_all()
    return _format_opps(engine.get_by_category(category), fmt)


@router.get("/history")
def opportunity_history(period: Optional[str] = Query(None), limit: int = Query(30, ge=1, le=365)):
    """Historical snapshots for trend analysis."""
    engine = get_engine()
    snaps = engine.get_history(period, limit)
    return {
        "snapshots": [
            {
                "id": s.id,
                "timestamp": s.timestamp,
                "period": s.period,
                "opportunity_count": len(s.opportunities),
                "metrics": s.metrics,
            }
            for s in snaps
        ],
        "trends": engine.get_history().get_trends() if snaps else {},
        "count": len(snaps),
    }


@router.get("/providers")
def list_providers():
    """List registered opportunity providers and their status."""
    engine = get_engine()
    return {
        "providers": [
            {"name": p.name, "category": p.category, "opportunity_count": p.opportunity_count,
             "health_status": p.health_status}
            for p in engine.get_providers_info()
        ]
    }
