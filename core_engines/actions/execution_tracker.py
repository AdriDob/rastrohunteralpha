"""ExecutionTracker — tracks every action execution with timing and outcome scoring."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rastro.actions.tracker")


@dataclass
class ExecutionRecord:
    action_id: str
    action_type: str
    label: str
    status: str  # executed | error | skipped
    duration_ms: float = 0.0
    user_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    outcome_score: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "label": self.label,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "user_id": self.user_id,
            "payload": self.payload,
            "result": self.result,
            "error": self.error,
            "outcome_score": round(self.outcome_score, 3),
            "timestamp": self.timestamp,
        }


class ExecutionTracker:
    """Tracks execution of every action with timing, outcome, and scoring.

    Maintains an in-memory buffer with automatic archival to persistent memory.
    """

    BUFFER_SIZE = 200

    def __init__(self) -> None:
        self._records: List[ExecutionRecord] = []
        self._type_stats: Dict[str, Dict[str, float]] = {}

    def record_execution(
        self,
        action_id: str,
        action_type: str,
        label: str,
        status: str = "executed",
        duration_ms: float = 0.0,
        user_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> ExecutionRecord:
        outcome_score = self._compute_outcome_score(status, error, duration_ms)
        record = ExecutionRecord(
            action_id=action_id,
            action_type=action_type,
            label=label,
            status=status,
            duration_ms=duration_ms,
            user_id=user_id,
            payload=payload or {},
            result=result or {},
            error=error,
            outcome_score=outcome_score,
        )
        self._records.append(record)
        if len(self._records) > self.BUFFER_SIZE:
            self._records = self._records[-self.BUFFER_SIZE:]

        self._update_type_stats(action_type, outcome_score, duration_ms, status)

        self._archive_to_memory(record)

        return record

    def _compute_outcome_score(self, status: str, error: Optional[str], duration_ms: float) -> float:
        if status == "error":
            return 0.0
        if status == "skipped":
            return 0.3
        score = 0.8
        if error:
            score -= 0.3
        if duration_ms > 5000:
            score -= 0.1
        elif duration_ms < 100:
            score += 0.1
        return max(0.0, min(1.0, score))

    def _update_type_stats(self, action_type: str, outcome_score: float, duration_ms: float, status: str) -> None:
        if action_type not in self._type_stats:
            self._type_stats[action_type] = {
                "count": 0, "total_score": 0.0, "total_duration": 0.0,
                "errors": 0, "avg_score": 0.0, "avg_duration": 0.0,
            }
        stats = self._type_stats[action_type]
        stats["count"] += 1
        stats["total_score"] += outcome_score
        stats["total_duration"] += duration_ms
        if status == "error":
            stats["errors"] += 1
        stats["avg_score"] = stats["total_score"] / stats["count"]
        stats["avg_duration"] = stats["total_duration"] / stats["count"]

    def _archive_to_memory(self, record: ExecutionRecord) -> None:
        try:
            from core.memory.decision_memory import get_decision_memory
            from core.memory.decision_memory import Decision
            memory = get_decision_memory()
            decision = Decision(
                id=f"exec-{record.action_id}-{int(record.timestamp)}",
                action=record.action_id,
                reason=f"Executed {record.action_type}: {record.label}",
                confidence=record.outcome_score,
                source="execution_tracker",
                context={
                    "duration_ms": record.duration_ms,
                    "status": record.status,
                    "payload": record.payload,
                },
                outcome=record.status,
            )
            memory.record_decision(decision)
        except Exception as exc:
            logger.debug("Failed to archive execution to memory: %s", exc)

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_executions": len(self._records),
            "by_type": self._type_stats,
            "recent": self.get_recent(5),
        }

    def get_type_stats(self, action_type: str) -> Dict[str, float]:
        return self._type_stats.get(action_type, {
            "count": 0, "avg_score": 0.0, "avg_duration": 0.0,
            "errors": 0,
        })

    def clear(self) -> None:
        self._records.clear()
        self._type_stats.clear()


_TRACKER: Optional[ExecutionTracker] = None


def get_execution_tracker() -> ExecutionTracker:
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = ExecutionTracker()
    return _TRACKER
