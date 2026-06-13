"""SystemScorecard — aggregate metrics dashboard for system effectiveness.

Measures:
- how many actions were executed
- success rate by type
- average outcome scores
- total value delivered
- system health indicators
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rastro.accountability.scorecard")


@dataclass
class ScorecardMetrics:
    period_start: float = 0.0
    period_end: float = 0.0
    total_actions: int = 0
    success_rate: float = 0.0
    avg_outcome_score: float = 0.0
    total_value_delivered: float = 0.0
    by_type: Dict[str, Any] = field(default_factory=dict)
    system_health: str = "healthy"
    active_decisions: int = 0
    memory_usage: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_actions": self.total_actions,
            "success_rate": round(self.success_rate, 3),
            "avg_outcome_score": round(self.avg_outcome_score, 3),
            "total_value_delivered": round(self.total_value_delivered, 3),
            "by_type": self.by_type,
            "system_health": self.system_health,
            "active_decisions": self.active_decisions,
            "memory_usage": self.memory_usage,
        }


class SystemScorecard:
    """Aggregate scorecard of system performance and effectiveness."""

    def __init__(self) -> None:
        self._history: List[ScorecardMetrics] = []

    def generate(self) -> ScorecardMetrics:
        now = time.time()
        metrics = ScorecardMetrics(
            period_start=now - 3600,
            period_end=now,
        )

        try:
            from core.actions.execution_tracker import get_execution_tracker
            tracker = get_execution_tracker()
            stats = tracker.get_stats()
            by_type = stats.get("by_type", {})
            metrics.total_actions = stats.get("total_executions", 0)
            type_summary: Dict[str, Any] = {}
            total_score = 0.0
            total_val = 0.0
            score_count = 0
            for t, s in by_type.items():
                type_summary[t] = {
                    "count": s.get("count", 0),
                    "avg_score": s.get("avg_score", 0.0),
                    "avg_duration": s.get("avg_duration", 0.0),
                    "errors": s.get("errors", 0),
                }
                total_score += s.get("avg_score", 0.0) * s.get("count", 0)
                total_val += s.get("total_value", 0.0)
                score_count += s.get("count", 0)
            metrics.by_type = type_summary
            metrics.avg_outcome_score = total_score / score_count if score_count > 0 else 0.0
            metrics.total_value_delivered = total_val
        except Exception as exc:
            logger.debug("Failed to collect execution stats: %s", exc)

        try:
            from core.accountability.outcome_tracker import get_outcome_tracker
            o_tracker = get_outcome_tracker()
            summary = o_tracker.get_summary()
            metrics.success_rate = summary.get("success_rate", 0.5)
        except Exception as exc:
            logger.debug("Failed to collect outcome stats: %s", exc)

        try:
            from core.intelligence.priority_engine import get_priority_engine
            engine = get_priority_engine()
            metrics.active_decisions = engine.count()
        except Exception as exc:
            logger.debug("Failed to collect priority stats: %s", exc)

        try:
            from core.memory.insight_archive import get_insight_archive
            archive = get_insight_archive()
            metrics.memory_usage = archive.total_count()
        except Exception as exc:
            logger.debug("Failed to collect memory stats: %s", exc)

        metrics.system_health = self._compute_health(metrics)
        self._history.append(metrics)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        return metrics

    def _compute_health(self, metrics: ScorecardMetrics) -> str:
        if metrics.total_actions == 0:
            return "idle"
        if metrics.success_rate < 0.3:
            return "degraded"
        if metrics.success_rate < 0.6:
            return "warning"
        return "healthy"

    def get_latest(self) -> Optional[Dict[str, Any]]:
        if not self._history:
            return None
        return self._history[-1].to_dict()

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._history[-limit:]]

    def get_trend(self) -> Dict[str, Any]:
        if len(self._history) < 2:
            return {"trend": "insufficient_data"}
        recent = self._history[-5:]
        first_rate = recent[0].success_rate
        last_rate = recent[-1].success_rate
        delta = last_rate - first_rate
        return {
            "trend": "improving" if delta > 0.05 else "declining" if delta < -0.05 else "stable",
            "delta": round(delta, 3),
            "start_rate": round(first_rate, 3),
            "current_rate": round(last_rate, 3),
        }


_SCORECARD: Optional[SystemScorecard] = None


def get_system_scorecard() -> SystemScorecard:
    global _SCORECARD
    if _SCORECARD is None:
        _SCORECARD = SystemScorecard()
    return _SCORECARD
