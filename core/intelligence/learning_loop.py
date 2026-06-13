"""Closed Intelligence Loop — the system learns from usage.

Loop:
  1. SIGNAL  — incoming events, user actions, discovery results
  2. PROCESS — scoring → priority → recommendation
  3. ACTION  — assistant suggestions, UI highlights, notifications
  4. FEEDBACK — clicks, ignores, time-to-action, outcomes
  5. LEARNING — adjust weights, ranking, EVH estimation
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("rastro.intelligence.loop")

SignalHandler = Callable[[Dict[str, Any]], None]


@dataclass
class FeedbackEvent:
    action_id: str
    action_type: str
    outcome: str  # clicked | ignored | dismissed | completed
    latency: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningLoop:
    """Closed-loop intelligence: signal → process → act → feedback → learn."""

    def __init__(self) -> None:
        self._signal_handlers: Dict[str, List[SignalHandler]] = {}
        self._feedback_history: List[FeedbackEvent] = []
        self._success_rate: Dict[str, float] = {}
        self._weight_adjustments: Dict[str, float] = {}
        self._loop_count: int = 0

    # ── SIGNAL phase ──────────────────────────────────────────────────

    def register_signal_handler(self, signal_type: str, handler: SignalHandler) -> None:
        if signal_type not in self._signal_handlers:
            self._signal_handlers[signal_type] = []
        self._signal_handlers[signal_type].append(handler)

    def emit_signal(self, signal_type: str, payload: Dict[str, Any]) -> None:
        handlers = self._signal_handlers.get(signal_type, [])
        for handler in handlers:
            try:
                handler(payload)
            except Exception as exc:
                logger.warning("Signal handler error for %s: %s", signal_type, exc)
        self._loop_count += 1

    # ── PROCESS phase ─────────────────────────────────────────────────

    def process_through_priority(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        from core.intelligence.priority_engine import get_priority_engine
        engine = get_priority_engine()

        source = payload.get("source", "unknown")
        if source == "opportunity":
            engine.ingest_opportunity(payload)
        elif source == "quick_win":
            engine.ingest_quick_win(payload)
        elif source == "alert":
            engine.ingest_system_alert(payload)
        elif source == "recommendation":
            engine.ingest_assistant_recommendation(payload)

        ranked = engine.get_ranked(limit=10)
        return [a.to_dict() for a in ranked]

    # ── FEEDBACK phase ────────────────────────────────────────────────

    def record_feedback(self, event: FeedbackEvent) -> None:
        self._feedback_history.append(event)
        if len(self._feedback_history) > 1000:
            self._feedback_history = self._feedback_history[-1000:]

        key = event.action_type
        recent = [e for e in self._feedback_history[-50:] if e.action_type == key]
        if recent:
            successes = sum(1 for e in recent if e.outcome in ("clicked", "completed"))
            self._success_rate[key] = successes / len(recent)
        self._maybe_learn(event)

    def get_success_rate(self, action_type: str) -> float:
        return self._success_rate.get(action_type, 0.5)

    def get_feedback_stats(self) -> Dict[str, Any]:
        types = set(e.action_type for e in self._feedback_history)
        return {
            "total_events": len(self._feedback_history),
            "by_type": {t: self._success_rate.get(t, 0) for t in types},
            "loop_count": self._loop_count,
        }

    # ── LEARNING phase ────────────────────────────────────────────────

    def _maybe_learn(self, event: FeedbackEvent) -> None:
        key = event.action_type
        rate = self._success_rate.get(key, 0.5)
        adjustment = 0.0

        if event.outcome in ("clicked", "completed"):
            if rate > 0.6:
                adjustment = 0.02
        elif event.outcome == "ignored":
            if rate < 0.3:
                adjustment = -0.01

        if adjustment != 0:
            current = self._weight_adjustments.get(key, 0.0)
            self._weight_adjustments[key] = max(-0.5, min(0.5, current + adjustment))
            logger.debug(
                "Learned: %s rate=%.2f adj=%.3f",
                key, rate, self._weight_adjustments[key],
            )

    def get_weight_adjustment(self, action_type: str) -> float:
        return self._weight_adjustments.get(action_type, 0.0)

    def get_learning_summary(self) -> Dict[str, Any]:
        return {
            "success_rates": dict(self._success_rate),
            "weight_adjustments": dict(self._weight_adjustments),
            "loop_count": self._loop_count,
        }

    def reset_learning(self) -> None:
        self._success_rate.clear()
        self._weight_adjustments.clear()


_LEARNING_LOOP: Optional[LearningLoop] = None


def get_learning_loop() -> LearningLoop:
    global _LEARNING_LOOP
    if _LEARNING_LOOP is None:
        _LEARNING_LOOP = LearningLoop()
    return _LEARNING_LOOP
