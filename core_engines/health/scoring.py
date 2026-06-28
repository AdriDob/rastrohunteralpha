"""Health scoring — computes 0-100 health score from system metrics."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("rastro.health.scoring")

BASE_SCORE = 100.0

# Penalties
PENALTY_EVENTBUS_FAIL = 15.0
PENALTY_AGENT_CRASH = 10.0
PENALTY_SCHEDULER_LATENCY = 5.0
PENALTY_DB_LOCK = 12.0
PENALTY_PIPELINE_RETRY = 6.0
PENALTY_RECOVERY_ATTEMPT = 8.0
PENALTY_MEMORY_HIGH = 7.0
PENALTY_CIRCUIT_OPEN = 20.0


class HealthStatus(str, Enum):
    OK = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"


def classify_health(score: float) -> HealthStatus:
    if score >= 80:
        return HealthStatus.OK
    if score >= 50:
        return HealthStatus.DEGRADED
    if score >= 25:
        return HealthStatus.CRITICAL
    return HealthStatus.RECOVERING


def compute_health_score(metrics: dict[str, Any]) -> float:
    score = BASE_SCORE

    score -= metrics.get("eventbus_failures", 0) * PENALTY_EVENTBUS_FAIL
    score -= metrics.get("agent_crashes", 0) * PENALTY_AGENT_CRASH
    score -= metrics.get("scheduler_latency_sec", 0) / 10 * PENALTY_SCHEDULER_LATENCY
    score -= metrics.get("db_lock_count", 0) * PENALTY_DB_LOCK
    score -= metrics.get("pipeline_retries", 0) * PENALTY_PIPELINE_RETRY
    score -= metrics.get("recovery_attempts", 0) * PENALTY_RECOVERY_ATTEMPT
    score -= max(0, (metrics.get("memory_percent", 0) - 60)) / 10 * PENALTY_MEMORY_HIGH
    score -= metrics.get("open_circuits", 0) * PENALTY_CIRCUIT_OPEN

    return max(0.0, min(100.0, score))


class HealthScoringSystem:
    """Tracks system metrics and computes health scores over time."""

    def __init__(self, window_size: int = 100) -> None:
        self._window_size = window_size
        self._snapshots: list[dict[str, Any]] = []

    def record(self, metrics: dict[str, Any]) -> float:
        score = compute_health_score(metrics)
        self._snapshots.append({"score": score, **metrics})
        if len(self._snapshots) > self._window_size:
            self._snapshots[:] = self._snapshots[-self._window_size:]
        return score

    def current_score(self) -> float:
        if not self._snapshots:
            return BASE_SCORE
        return self._snapshots[-1]["score"]

    def current_status(self) -> HealthStatus:
        return classify_health(self.current_score())

    def history(self) -> list[dict[str, Any]]:
        return list(self._snapshots)

    def trend(self) -> str:
        if len(self._snapshots) < 5:
            return "stable"
        recent = [s["score"] for s in self._snapshots[-5:]]
        if all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1)):
            return "improving"
        if all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1)):
            return "declining"
        return "stable"
