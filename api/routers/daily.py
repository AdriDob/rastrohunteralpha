"""Daily Mode — primary entry point for Rastro.

Returns a curated briefing of what matters most right now.
Cached aggressively for <200ms response time.

Optimizations (cold start):
  - Heavy imports lazy-loaded inside request functions
  - Minimal endpoint returns skeleton data fast
  - Full briefing uses 30s server cache
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("rastro.api.daily")

router = APIRouter(prefix="/api/daily", tags=["daily"])

_CACHE: dict[str, Any] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 30
_CACHE_KEY = "briefing"


def _get_engine():
    from core_engines.opportunity import get_engine as _get_engine
    return _get_engine()


def _get_priority():
    from core_engines.intelligence.priority_engine import get_priority_engine as _get_priority
    return _get_priority()


def _get_orchestrator():
    from core_engines.orchestrator.assistant_orchestrator import get_orchestrator as _get_orch
    return _get_orch()


@router.get("/briefing")
async def daily_briefing():
    now = time.time()
    with _CACHE_LOCK:
        cached = _CACHE.get(_CACHE_KEY)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        return {"data": {"briefing": cached["data"], "cached": True}}

    try:
        opp_engine = _get_engine()
        priority = _get_priority()
        orchestrator = _get_orchestrator()

        top_opps = _top_opportunities(opp_engine, limit=2)
        risk_alerts = _get_risk_alerts(limit=1)
        quick_wins = _get_quick_wins(limit=1)
        recommended = orchestrator.recommend_next_action(1)
        system_health = _get_system_health()
        insight = _build_assistant_insight(priority, opp_engine)

        from core_engines.ux.info_filter import reduce_briefing

        daily_summary = {
            "opportunities": top_opps,
            "critical_risk": risk_alerts[0] if risk_alerts else None,
            "quick_win": quick_wins[0] if quick_wins else None,
            "recommended_action": recommended[0].to_dict() if recommended else None,
            "system_health": system_health,
            "assistant_insight": insight,
        }

        reduced = reduce_briefing(daily_summary)

        with _CACHE_LOCK:
            _CACHE[_CACHE_KEY] = {"data": reduced, "ts": now}
            if len(_CACHE) > 10:
                stale_keys = [k for k, v in _CACHE.items() if k != _CACHE_KEY]
                for k in stale_keys:
                    del _CACHE[k]

        try:
            priority.ingest_user_signal("daily_briefing", "daily", weight=0.05)
        except Exception as e:
            logger.debug("Signal ingestion skipped: %s", e)

        return {"data": {"briefing": reduced, "cached": False}}
    except Exception as exc:
        logger.warning("Briefing generation failed: %s", exc, exc_info=True)
        return {
            "data": {
                "briefing": {
                    "opportunities": [],
                    "critical_risk": None,
                    "quick_win": None,
                    "recommended_action": None,
                    "system_health": {"status": "UNKNOWN", "services_healthy": 0, "services_total": 0},
                    "assistant_insight": {
                        "focus": "Exploring",
                        "reason": "Discovery active",
                        "system_state": "0 opps",
                    },
                },
                "cached": False,
            }
        }


@router.get("/minimal")
async def minimal_briefing():
    """Ultra-fast endpoint: returns only system health + recommended action."""
    system_health = _get_system_health()
    try:
        orchestrator = _get_orchestrator()
        recommended = orchestrator.recommend_next_action(1)
        top = recommended[0].to_dict() if recommended else None
    except Exception:
        top = None

    return {
        "data": {
            "system_health": system_health,
            "recommended_action": top,
        }
    }


@router.post("/refresh")
async def refresh_briefing():
    _CACHE.pop(_CACHE_KEY, None)
    return await daily_briefing()


def _top_opportunities(engine, limit: int = 2) -> list:
    from core_engines.ux.info_filter import truncate
    opportunities = engine.get_all()
    scored = []
    for o in opportunities:
        score_val = o.score.overall if o.score else 0.0
        payout = o.estimated_payout or 0
        scored.append({
            "id": o.id,
            "name": truncate(o.name, 60),
            "category": o.category,
            "score": round(score_val, 2),
            "estimated_payout": payout,
            "priority": o.priority or "medium",
        })
    scored.sort(key=lambda x: (x["score"], x["estimated_payout"]), reverse=True)
    return scored[:limit]


def _get_risk_alerts(limit: int = 1) -> list:
    from database import db, models
    session = db.SessionLocal()
    try:
        rows = session.query(models.Finding).filter(
            models.Finding.severity.in_(["critical", "high"])
        ).order_by(models.Finding.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "severity": r.severity,
                "description": (r.description or "")[:120],
                "created_at": str(r.created_at or ""),
            }
            for r in rows
        ]
    finally:
        session.close()


def _get_quick_wins(limit: int = 1) -> list:
    from database import db, models
    session = db.SessionLocal()
    try:
        rows = session.query(models.Finding).filter(
            models.Finding.severity.in_(["critical", "high"])
        ).order_by(models.Finding.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "category": r.severity or "high",
                "estimated_payout": 0,
                "confidence": 0.75,
            }
            for r in rows
        ]
    except Exception:
        return []
    finally:
        session.close()


def _get_system_health() -> dict:
    try:
        from core_engines.system_state import get_system_state
        state = get_system_state()
        summary = state.get_summary()
        return {
            "status": summary.get("system_state", "UNKNOWN"),
            "services_healthy": summary.get("services_healthy", 0),
            "services_total": summary.get("services_total", 0),
        }
    except Exception:
        return {"status": "UNKNOWN", "services_healthy": 0, "services_total": 0}


def _build_assistant_insight(priority, opp_engine) -> dict:
    from core_engines.ux.info_filter import truncate
    top = priority.get_top(1)
    metrics = opp_engine.get_metrics()
    total = metrics.get("opportunities_total", 0)
    high = metrics.get("by_priority", {}).get("high", 0)
    if top:
        return {
            "focus": truncate(top[0].label, 60),
            "reason": truncate(f"Top priority ({top[0].category})", 80),
            "system_state": f"{total} opps · {high} high",
        }
    return {
        "focus": "Exploring",
        "reason": "Discovery active",
        "system_state": f"{total} opps · {high} high",
    }
