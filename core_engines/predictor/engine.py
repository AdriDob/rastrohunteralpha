"""FailurePredictionSystem — predicts failures based on historical data.

Analyzes error history to calculate failure probability per component
and emit preventive alerts.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("rastro.predictor.engine")

PREDICTION_WINDOW = 300


class RiskLevel(str, Enum):
    LOW = "low_risk"
    MEDIUM = "medium_risk"
    HIGH = "high_risk"


@dataclass
class FailurePrediction:
    component: str
    risk_level: RiskLevel
    probability: float  # 0.0 – 1.0
    predicted_failure_type: str
    evidence: list[str]
    generated_at: str
    recommended_action: str = ""


class FailurePredictionSystem:
    """Predicts future failures by analyzing historical error patterns.

    Uses simple statistical methods:
    - Frequency analysis: components that fail often are likely to fail again
    - Recency weighting: recent failures are stronger predictors
    - Co-occurrence: some failures tend to precede others
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._error_history: list[dict[str, Any]] = []
        self._max_history = PREDICTION_WINDOW
        self._co_occurrence: dict[str, Counter] = defaultdict(Counter)

    def record_failure(
        self,
        component: str,
        failure_type: str,
        error_message: str = "",
    ) -> None:
        with self._lock:
            entry = {
                "component": component,
                "failure_type": failure_type,
                "error_message": error_message[:200],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._error_history.append(entry)

            # Track co-occurrence (which failures follow which)
            if len(self._error_history) >= 2:
                prev = self._error_history[-2]
                if prev["component"] != component:
                    self._co_occurrence[prev["component"]][component] += 1
                    self._co_occurrence[prev["failure_type"]][failure_type] += 1

            if len(self._error_history) > self._max_history:
                self._error_history[:] = self._error_history[-self._max_history // 2:]

    # ── Prediction ────────────────────────────────────────────────────

    def predict(self, component: str | None = None) -> list[FailurePrediction]:
        with self._lock:
            if not self._error_history:
                return []

            predictions: list[FailurePrediction] = []
            now = datetime.now(timezone.utc).timestamp()

            components = [component] if component else list(set(e["component"] for e in self._error_history))

            for comp in components:
                comp_errors = [
                    e for e in self._error_history if e["component"] == comp
                ]
                if not comp_errors:
                    continue

                # Base probability from frequency
                total_errors = len(comp_errors)
                base_prob = min(1.0, total_errors / 20)

                # Recency weight: more recent = higher probability
                recency_weight = 0.0
                for e in comp_errors[-10:]:
                    try:
                        e_time = datetime.fromisoformat(e["timestamp"]).timestamp()
                        hours_ago = (now - e_time) / 3600
                        if hours_ago < 1:
                            recency_weight += 0.3
                        elif hours_ago < 6:
                            recency_weight += 0.15
                        elif hours_ago < 24:
                            recency_weight += 0.05
                    except Exception:
                        pass
                recency_factor = min(1.0, recency_weight)

                # Combined probability
                probability = min(1.0, base_prob * 0.6 + recency_factor * 0.4)

                # Most common failure type for this component
                failure_types = Counter(e["failure_type"] for e in comp_errors)
                predicted_type = failure_types.most_common(1)[0][0] if failure_types else "unknown"

                # Risk level
                if probability > 0.6:
                    risk = RiskLevel.HIGH
                elif probability > 0.3:
                    risk = RiskLevel.MEDIUM
                else:
                    risk = RiskLevel.LOW

                # Evidence
                evidence = [
                    f"{total_errors} past failures recorded",
                    f"Most common: {predicted_type} ({failure_types[predicted_type]}x)",
                    f"Recency factor: {recency_factor:.2f}",
                ]

                # Recommended action for high risk
                action = ""
                if risk == RiskLevel.HIGH:
                    if "eventbus" in comp.lower() or "event_bus" in comp.lower():
                        action = "reset_event_bus"
                    elif "agent" in comp.lower():
                        action = f"restart_agent:{comp}"
                    elif "scheduler" in comp.lower():
                        action = "restart_scheduler"
                    elif "db" in comp.lower() or "database" in comp.lower():
                        action = "reopen_db_connection"
                    else:
                        action = "inspect_component"

                predictions.append(FailurePrediction(
                    component=comp,
                    risk_level=risk,
                    probability=round(probability, 2),
                    predicted_failure_type=predicted_type,
                    evidence=evidence,
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    recommended_action=action,
                ))

            predictions.sort(key=lambda p: p.probability, reverse=True)
            return predictions

    def predict_next_failure(self) -> FailurePrediction | None:
        """Return the single most likely future failure."""
        predictions = self.predict()
        return predictions[0] if predictions else None

    def get_risk_summary(self) -> dict[str, Any]:
        predictions = self.predict()
        return {
            "total_predictions": len(predictions),
            "high_risk": sum(1 for p in predictions if p.risk_level == RiskLevel.HIGH),
            "medium_risk": sum(1 for p in predictions if p.risk_level == RiskLevel.MEDIUM),
            "low_risk": sum(1 for p in predictions if p.risk_level == RiskLevel.LOW),
            "highest_risk": predictions[0] if predictions else None,
        }

    def clear(self) -> None:
        with self._lock:
            self._error_history.clear()
            self._co_occurrence.clear()


_PREDICTOR: FailurePredictionSystem | None = None
_PREDICTOR_LOCK = threading.Lock()


def get_failure_predictor() -> FailurePredictionSystem:
    global _PREDICTOR
    if _PREDICTOR is None:
        with _PREDICTOR_LOCK:
            if _PREDICTOR is None:
                _PREDICTOR = FailurePredictionSystem()
    return _PREDICTOR


def reset_failure_predictor() -> None:
    global _PREDICTOR
    _PREDICTOR = None
