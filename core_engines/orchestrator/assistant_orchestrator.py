"""Assistant Orchestrator — the system control surface.

The assistant no longer responds. It decides system behavior:
  - what to show
  - what to hide
  - what to recommend next
  - when to refresh
  - what to suppress
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("rastro.orchestrator.assistant")

MIN_CONFIDENCE = 0.3


@dataclass
class OrchestratorDecision:
    action: str
    label: str
    reason: str
    confidence: float = 0.0
    priority: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "label": self.label,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "priority": self.priority,
            "context": self.context,
            "payload": self.payload,
        }


class AssistantOrchestrator:
    """Decides system behavior based on priority engine + learning loop."""

    def __init__(self) -> None:
        self._decisions: dict[str, OrchestratorDecision] = {}
        self._suppressed: dict[str, float] = {}

    def recommend_next_action(self, top_n: int = 3) -> list[OrchestratorDecision]:
        from core_engines.intelligence.priority_engine import get_priority_engine
        engine = get_priority_engine()
        ranked = engine.get_ranked(limit=top_n + 5)
        decisions: list[OrchestratorDecision] = []
        for action in ranked:
            if action.id in self._suppressed:
                continue
            decision = OrchestratorDecision(
                action=action.action_type,
                label=action.label,
                reason=action.description,
                confidence=action.combined_score,
                priority=int(action.combined_score * 100),
                payload={"route": action.route, "id": action.id, **action.payload},
            )
            decisions.append(decision)
            self._decisions[action.id] = decision
            if len(decisions) >= top_n:
                break
        return decisions

    def auto_prioritize_dashboard(self) -> dict[str, Any]:
        decisions = self.recommend_next_action(5)
        if not decisions:
            return {"top_action": None, "decisions": []}

        return {
            "top_action": decisions[0].to_dict() if decisions else None,
            "decisions": [d.to_dict() for d in decisions],
            "generated_at": time.time(),
        }

    def highlight_ui_elements(self) -> list[dict[str, Any]]:
        from core_engines.intelligence.priority_engine import get_priority_engine
        engine = get_priority_engine()
        top = engine.get_top(3)
        return [
            {
                "element": "priority_card",
                "action_id": a.id,
                "label": a.label,
                "score": a.combined_score,
                "route": a.route,
            }
            for a in top
            if a.id not in self._suppressed
        ]

    def suppress_noise_items(self, threshold: float = 0.15) -> int:
        from core_engines.intelligence.priority_engine import get_priority_engine
        engine = get_priority_engine()
        ranked = engine.get_ranked(limit=100)
        count = 0
        now = time.time()
        for action in ranked:
            if action.combined_score < threshold:
                self._suppressed[action.id] = now
                count += 1
        logger.info("Suppressed %d noise items (threshold=%.2f)", count, threshold)
        return count

    def trigger_discovery_refresh(self) -> OrchestratorDecision | None:
        from core_engines.intelligence.learning_loop import get_learning_loop
        loop = get_learning_loop()
        success_rate = loop.get_success_rate("open_opportunity")
        if success_rate < 0.3:
            return None
        decision = OrchestratorDecision(
            action="refresh_discovery",
            label="Refresh Intelligence",
            reason=f"Success rate {success_rate:.0%} — new signals may improve ranking",
            confidence=success_rate,
            priority=3,
            payload={"route": "/intelligence", "action": "refresh"},
        )
        return decision

    def get_active_suppressions(self) -> list[str]:
        now = time.time()
        return [aid for aid, ts in self._suppressed.items() if now - ts < 3600]

    def unsuppress(self, action_id: str) -> None:
        self._suppressed.pop(action_id, None)

    def clear_suppressions(self) -> None:
        self._suppressed.clear()

    def get_decisions(self) -> dict[str, Any]:
        return {
            "active_decisions": len(self._decisions),
            "suppressed": len(self._suppressed),
            "next_action": self.recommend_next_action(1)[0].to_dict() if self.recommend_next_action(1) else None,
        }


_ORCHESTRATOR: AssistantOrchestrator | None = None


def get_orchestrator() -> AssistantOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = AssistantOrchestrator()
    return _ORCHESTRATOR
