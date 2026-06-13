"""OutcomeTracker — tracks real-world outcomes of every system action.

Every action execution produces an outcome entry that records:
- what was done
- what happened (success / failure / partial)
- measurable result (score, time saved, issues found, etc.)
- who/what triggered it
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rastro.accountability.outcome")

CATEGORY = "outcome"


@dataclass
class OutcomeEntry:
    action_id: str
    action_type: str
    label: str
    result: str  # success | failure | partial | unknown
    value_score: float = 0.0
    duration_ms: float = 0.0
    source: str = "system"
    details: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "label": self.label,
            "result": self.result,
            "value_score": round(self.value_score, 3),
            "duration_ms": round(self.duration_ms, 2),
            "source": self.source,
            "details": self.details,
            "user_id": self.user_id,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class OutcomeTracker:
    """Tracks outcomes of actions and produces aggregate metrics."""

    MAX_HISTORY = 1000

    def __init__(self) -> None:
        self._outcomes: List[OutcomeEntry] = []

    def record(self, entry: OutcomeEntry) -> None:
        self._outcomes.append(entry)
        if len(self._outcomes) > self.MAX_HISTORY:
            self._outcomes = self._outcomes[-self.MAX_HISTORY:]
        self._archive(entry)

    def _archive(self, entry: OutcomeEntry) -> None:
        try:
            from core.memory.insight_archive import get_insight_archive, Insight
            archive = get_insight_archive()
            insight = Insight(
                id=f"outcome-{entry.action_id}-{int(entry.timestamp)}",
                title=f"Outcome: {entry.action_type} - {entry.result}",
                description=f"{entry.label}: {entry.result} (score: {entry.value_score:.2f})",
                insight_type="outcome",
                source=entry.source,
                severity="info",
                tags=["outcome", entry.result, entry.action_type],
                context=entry.to_dict(),
            )
            archive.archive(insight)
        except Exception as exc:
            logger.debug("Failed to archive outcome: %s", exc)

    def get_success_rate(self, action_type: Optional[str] = None) -> float:
        relevant = self._outcomes
        if action_type:
            relevant = [o for o in relevant if o.action_type == action_type]
        if not relevant:
            return 0.5
        successes = sum(1 for o in relevant if o.result == "success")
        return successes / len(relevant)

    def get_by_type(self, action_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        matching = [o for o in self._outcomes if o.action_type == action_type]
        return [o.to_dict() for o in matching[-limit:]]

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [o.to_dict() for o in self._outcomes[-limit:]]

    def get_summary(self) -> Dict[str, Any]:
        if not self._outcomes:
            return {"total": 0, "success_rate": 0.5, "by_type": {}}
        by_type: Dict[str, Dict[str, Any]] = {}
        for o in self._outcomes:
            if o.action_type not in by_type:
                by_type[o.action_type] = {"count": 0, "successes": 0, "total_value": 0.0}
            by_type[o.action_type]["count"] += 1
            if o.result == "success":
                by_type[o.action_type]["successes"] += 1
            by_type[o.action_type]["total_value"] += o.value_score
        for t, stats in by_type.items():
            stats["success_rate"] = stats["successes"] / stats["count"] if stats["count"] > 0 else 0.5
            stats["avg_value"] = stats["total_value"] / stats["count"] if stats["count"] > 0 else 0.0
        total_successes = sum(1 for o in self._outcomes if o.result == "success")
        return {
            "total": len(self._outcomes),
            "success_rate": total_successes / len(self._outcomes),
            "by_type": by_type,
        }

    def count(self) -> int:
        return len(self._outcomes)


_TRACKER: Optional[OutcomeTracker] = None


def get_outcome_tracker() -> OutcomeTracker:
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = OutcomeTracker()
    return _TRACKER
