"""Global Priority Engine — unifies every signal into a single ranked action list.

Inputs:
  - opportunities (EVH + score)
  - quick wins
  - system alerts
  - assistant recommendations
  - historical success rate
  - user interaction signals

Output:
  GlobalPriorityList — ranked_actions ordered by combined urgency × expected value.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("rastro.intelligence.priority")

URGENCY_WEIGHT = 0.4
VALUE_WEIGHT = 0.35
CONFIDENCE_WEIGHT = 0.15
RECENCY_WEIGHT = 0.1

MAX_AGE_HOURS = 72


@dataclass
class PrioritizedAction:
    id: str
    action_type: str
    label: str
    description: str
    urgency_score: float = 0.0
    expected_value_score: float = 0.0
    confidence_score: float = 0.0
    combined_score: float = 0.0
    source: str = ""
    category: str = "general"
    route: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "label": self.label,
            "description": self.description,
            "urgency_score": round(self.urgency_score, 3),
            "expected_value_score": round(self.expected_value_score, 3),
            "confidence_score": round(self.confidence_score, 3),
            "combined_score": round(self.combined_score, 3),
            "source": self.source,
            "category": self.category,
            "route": self.route,
            "payload": self.payload,
        }


class PriorityEngine:
    """Ranks all signals into a single ordered action list."""

    def __init__(self) -> None:
        self._actions: dict[str, PrioritizedAction] = {}

    def ingest_opportunity(self, opp: dict[str, Any]) -> None:
        score = opp.get("score", 0)
        payout = opp.get("estimated_payout", 0)
        evh = opp.get("evh_score", score)
        action = PrioritizedAction(
            id=f"opp-{opp.get('id', hash(str(opp)))}",
            action_type="open_opportunity",
            label=opp.get("name", "Opportunity"),
            description=f"EVH {evh:.2f} · ${payout:,} est.",
            urgency_score=min(evh / 100, 1.0),
            expected_value_score=min(payout / 10000, 1.0),
            confidence_score=opp.get("confidence", 0.5),
            source="opportunity_engine",
            category=opp.get("category", "general"),
            route="/radar",
            payload={"id": opp.get("id"), "name": opp.get("name")},
        )
        self._compute_and_store(action)

    def ingest_quick_win(self, qw: dict[str, Any]) -> None:
        confidence = qw.get("confidence", 0)
        payout = qw.get("estimated_payout", 0)
        action = PrioritizedAction(
            id=f"qw-{qw.get('id', hash(str(qw)))}",
            action_type="quick_win",
            label=qw.get("title", "Quick Win"),
            description=f"Confidence {confidence:.0%} · ${payout:,}",
            urgency_score=confidence,
            expected_value_score=min(payout / 5000, 1.0),
            confidence_score=confidence,
            source="quick_win_engine",
            category="quick_win",
            route="/radar",
            payload={"id": qw.get("id"), "title": qw.get("title")},
        )
        self._compute_and_store(action)

    def ingest_system_alert(self, alert: dict[str, Any]) -> None:
        severity = alert.get("severity", "low")
        urgency = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2}.get(severity, 0.2)
        action = PrioritizedAction(
            id=f"alert-{alert.get('id', hash(str(alert)))}",
            action_type="system_alert",
            label=alert.get("title", "System Alert"),
            description=alert.get("message", ""),
            urgency_score=urgency,
            expected_value_score=0.5,
            confidence_score=1.0,
            source="system",
            category="alert",
            route=alert.get("route", "/"),
            payload=alert,
        )
        self._compute_and_store(action)

    def ingest_assistant_recommendation(self, rec: dict[str, Any]) -> None:
        priority = rec.get("priority", "medium")
        urgency = {"critical": 0.9, "high": 0.7, "medium": 0.4, "low": 0.1}.get(priority, 0.4)
        action = PrioritizedAction(
            id=f"rec-{rec.get('type', '')}-{rec.get('action', '')}".replace(" ", "-"),
            action_type=rec.get("action_type", "recommendation"),
            label=rec.get("action", "Recommendation"),
            description=rec.get("reason", ""),
            urgency_score=urgency,
            expected_value_score=rec.get("expected_value", 0.5),
            confidence_score=rec.get("confidence", 0.6),
            source="assistant",
            category="recommendation",
            route=rec.get("route", rec.get("endpoint")),
            payload=rec,
        )
        self._compute_and_store(action)

    def ingest_user_signal(self, action_type: str, target_id: str, weight: float = 0.1) -> None:
        key = f"user-{action_type}-{target_id}"
        existing = self._actions.get(key)
        if existing:
            existing.urgency_score = min(existing.urgency_score + weight, 1.0)
            existing.timestamp = time.time()
            self._recompute(existing)
        else:
            action = PrioritizedAction(
                id=key,
                action_type=action_type,
                label=f"Continue: {target_id}",
                description="Previously engaged item",
                urgency_score=weight,
                expected_value_score=0.3,
                confidence_score=0.5,
                source="user_signal",
                category="resume",
                route=f"/target/{target_id}" if action_type == "view_target" else "/",
                payload={"target_id": target_id},
            )
            self._compute_and_store(action)

    def _compute_and_store(self, action: PrioritizedAction) -> None:
        self._recompute(action)
        self._actions[action.id] = action

    def _recompute(self, action: PrioritizedAction) -> None:
        hours_old = (time.time() - action.timestamp) / 3600
        recency_factor = max(0, 1 - hours_old / MAX_AGE_HOURS)
        action.combined_score = (
            URGENCY_WEIGHT * action.urgency_score
            + VALUE_WEIGHT * action.expected_value_score
            + CONFIDENCE_WEIGHT * action.confidence_score
            + RECENCY_WEIGHT * recency_factor
        )

    def get_ranked(self, limit: int = 20, min_score: float = 0.0) -> list[PrioritizedAction]:
        now = time.time()
        valid = [
            a for a in self._actions.values()
            if (now - a.timestamp) / 3600 < MAX_AGE_HOURS
        ]
        valid.sort(key=lambda a: a.combined_score, reverse=True)
        return [a for a in valid if a.combined_score >= min_score][:limit]

    def get_top(self, n: int = 5) -> list[PrioritizedAction]:
        return self.get_ranked(limit=n, min_score=0.1)

    def get_by_category(self, category: str, limit: int = 10) -> list[PrioritizedAction]:
        return [
            a for a in self.get_ranked(limit=100)
            if a.category == category
        ][:limit]

    def clear_stale(self) -> int:
        now = time.time()
        stale = [k for k, a in self._actions.items() if (now - a.timestamp) / 3600 > MAX_AGE_HOURS]
        for k in stale:
            del self._actions[k]
        return len(stale)

    def count(self) -> int:
        return len(self._actions)

    def get_action(self, action_id: str) -> PrioritizedAction | None:
        return self._actions.get(action_id)

    def consume_memory(self) -> dict[str, Any]:
        """Query decision memory and insight archive to adjust scores."""
        enabled = os.environ.get("RASTRO_MEMORY_CONSUME", "true").lower() == "true"
        if not enabled:
            return {"status": "skipped", "reason": "memory consumption disabled"}
        try:
            from core_engines.memory.decision_memory import get_decision_memory
            memory = get_decision_memory()
            successes = 0
            failures = 0
            for action in self._actions.values():
                sr = memory.get_success_rate(action.action_type)
                if sr > 0.6:
                    action.confidence_score = min(action.confidence_score + 0.05, 1.0)
                    successes += 1
                elif sr < 0.3:
                    action.confidence_score = max(action.confidence_score - 0.05, 0.0)
                    failures += 1
                self._recompute(action)
            return {
                "status": "consumed",
                "actions_adjusted": len(self._actions),
                "boosted": successes,
                "reduced": failures,
            }
        except Exception as exc:
            logger.warning("Failed to consume memory: %s", exc)
            return {"status": "error", "error": str(exc)}

    def get_consumption_stats(self) -> dict[str, Any]:
        from core_engines.memory.decision_memory import get_decision_memory
        memory = get_decision_memory()
        return {
            "total_decisions": memory.count_decisions(),
            "success_rate_by_type": {
                at: memory.get_success_rate(at)
                for at in set(a.action_type for a in self._actions.values())
            },
        }


_PRIORITY: PriorityEngine | None = None


def get_priority_engine() -> PriorityEngine:
    global _PRIORITY
    if _PRIORITY is None:
        _PRIORITY = PriorityEngine()
    return _PRIORITY
