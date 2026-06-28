"""Graceful fallback layer — system always returns meaningful output.

Every key subsystem has a fallback that returns safe defaults
when the primary system is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("rastro.fallback")

_CACHED_BRIEFING: dict[str, Any] | None = None


def fallback_briefing() -> dict[str, Any]:
    """Return a safe default briefing when the intelligence engine fails."""
    global _CACHED_BRIEFING
    if _CACHED_BRIEFING:
        return _CACHED_BRIEFING
    return {
        "opportunities": [],
        "critical_risk": None,
        "quick_win": None,
        "recommended_action": {
            "action": "review_system",
            "label": "Review System Status",
            "reason": "Intelligence engine unavailable — system running in fallback mode",
            "confidence": 0.5,
            "payload": {},
        },
        "system_health": {"status": "DEGRADED", "services_healthy": 0, "services_total": 0},
        "assistant_insight": {
            "focus": "Fallback mode active",
            "reason": "System is running with limited intelligence — some features may be unavailable",
            "system_state": "Degraded operation",
        },
    }


def cache_briefing(data: dict[str, Any]) -> None:
    global _CACHED_BRIEFING
    _CACHED_BRIEFING = data


def fallback_priority_actions() -> list[dict[str, Any]]:
    return [
        {
            "id": "fallback-review",
            "action_type": "review",
            "label": "Review System",
            "description": "Priority engine unavailable — showing fallback actions",
            "urgency_score": 0.5,
            "expected_value_score": 0.3,
            "confidence_score": 0.5,
            "combined_score": 0.43,
            "source": "fallback",
            "category": "general",
            "route": "/",
        }
    ]


def fallback_scorecard() -> dict[str, Any]:
    return {
        "total_actions": 0,
        "success_rate": 0.5,
        "avg_outcome_score": 0.0,
        "total_value_delivered": 0.0,
        "by_type": {},
        "system_health": "degraded",
        "active_decisions": 0,
        "memory_usage": 0,
    }


def fallback_system_state() -> dict[str, Any]:
    return {
        "system_state": "DEGRADED",
        "services_healthy": 0,
        "services_total": 0,
        "services": [],
        "mode": "fallback",
    }
