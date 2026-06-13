"""ExplanationEngine — generates human-readable explanations for every system decision.

Every explanation includes:
- what was decided
- why (reasoning chain with input signals)
- confidence at decision time
- alternatives considered
- outcome (when known)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rastro.explainability.engine")

EXPLANATION_CATEGORY = "explanation"


@dataclass
class Explanation:
    id: str
    decision_id: str
    action: str
    summary: str
    reasoning_chain: List[str]
    confidence: float = 0.0
    source: str = "system"
    input_signals: List[Dict[str, Any]] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "action": self.action,
            "summary": self.summary,
            "reasoning_chain": self.reasoning_chain,
            "confidence": self.confidence,
            "source": self.source,
            "input_signals": self.input_signals,
            "alternatives": self.alternatives,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
        }


class ExplanationEngine:
    """Generates, stores, and retrieves explanations for system decisions."""

    def __init__(self) -> None:
        self._explanations: Dict[str, Explanation] = {}

    def explain(
        self,
        decision_id: str,
        action: str,
        summary: str,
        reasoning_chain: List[str],
        confidence: float = 0.0,
        source: str = "system",
        input_signals: Optional[List[Dict[str, Any]]] = None,
        alternatives: Optional[List[str]] = None,
    ) -> Explanation:
        explanation = Explanation(
            id=f"expl-{decision_id}",
            decision_id=decision_id,
            action=action,
            summary=summary,
            reasoning_chain=reasoning_chain,
            confidence=confidence,
            source=source,
            input_signals=input_signals or [],
            alternatives=alternatives or [],
        )
        self._explanations[explanation.id] = explanation
        self._archive(explanation)
        return explanation

    def get_explanation(self, decision_id: str) -> Optional[Explanation]:
        # Look up by decision_id directly
        for exp in self._explanations.values():
            if exp.decision_id == decision_id:
                return exp
        return None

    def get_explanation_by_id(self, explanation_id: str) -> Optional[Explanation]:
        return self._explanations.get(explanation_id)

    def explain_feedback(self, action: str, outcome: str) -> Explanation:
        decision_id = f"fb-{action}-{int(time.time())}"
        alternatives = ["no_action", "different_priority"]
        reasoning = [
            f"User action '{action}' completed with outcome '{outcome}'",
            f"Recording feedback for learning loop adjustment",
        ]
        return self.explain(
            decision_id=decision_id,
            action=action,
            summary=f"Feedback recorded for {action}: {outcome}",
            reasoning_chain=reasoning,
            confidence=1.0,
            source="user_feedback",
            alternatives=alternatives,
        )

    def explain_priority_rank(self, action_id: str, score: float, signals: List[str]) -> Explanation:
        decision_id = f"prio-{action_id}-{int(time.time())}"
        reasoning = [
            f"Priority score: {score:.3f}",
            *[f"Signal: {s}" for s in signals],
        ]
        return self.explain(
            decision_id=decision_id,
            action=f"rank:{action_id}",
            summary=f"Ranked {action_id} at {score:.3f}",
            reasoning_chain=reasoning,
            confidence=min(score + 0.2, 1.0),
            source="priority_engine",
            input_signals=[{"type": s} for s in signals],
        )

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        sorted_exps = sorted(
            self._explanations.values(),
            key=lambda e: e.timestamp,
            reverse=True,
        )
        return [e.to_dict() for e in sorted_exps[:limit]]

    def _archive(self, explanation: Explanation) -> None:
        try:
            from core.memory.insight_archive import get_insight_archive, Insight
            archive = get_insight_archive()
            insight = Insight(
                id=explanation.id,
                title=f"Explanation: {explanation.action}",
                description=explanation.summary,
                insight_type="explanation",
                source=explanation.source,
                severity="info",
                tags=["explanation", explanation.action, explanation.source],
                context={
                    "decision_id": explanation.decision_id,
                    "reasoning_chain": explanation.reasoning_chain,
                    "confidence": explanation.confidence,
                    "alternatives": explanation.alternatives,
                },
            )
            archive.archive(insight)
        except Exception as exc:
            logger.debug("Failed to archive explanation: %s", exc)

    def count(self) -> int:
        return len(self._explanations)

    def clear(self) -> None:
        self._explanations.clear()


_ENGINE: Optional[ExplanationEngine] = None


def get_explanation_engine() -> ExplanationEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ExplanationEngine()
    return _ENGINE
