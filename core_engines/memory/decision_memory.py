"""DecisionMemory — tracks every system decision and its rationale."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core_engines.memory.memory_store import get_memory_store, MemoryStore

logger = logging.getLogger("rastro.memory.decision")

CATEGORY = "decision"


@dataclass
class Decision:
    id: str
    action: str
    reason: str
    confidence: float = 0.0
    source: str = "system"
    context: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "reason": self.reason,
            "confidence": self.confidence,
            "source": self.source,
            "context": self.context,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
        }


class DecisionMemory:
    """Stores and retrieves system decisions with full provenance.

    Every decision is persisted with:
    - what action was chosen
    - why (reasoning chain)
    - confidence at decision time
    - context (inputs that led to the decision)
    - outcome (filled in later when known)
    """

    def __init__(self) -> None:
        self._store: MemoryStore = get_memory_store()

    def record_decision(self, decision: Decision) -> None:
        self._store.store(CATEGORY, decision.id, decision.to_dict())

    def record_outcome(self, decision_id: str, outcome: str) -> bool:
        existing = self._store.get(CATEGORY, decision_id)
        if existing is None:
            return False
        existing["outcome"] = outcome
        self._store.store(CATEGORY, decision_id, existing)
        return True

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(CATEGORY, decision_id)

    def list_decisions(
        self,
        limit: int = 50,
        offset: int = 0,
        only_with_outcomes: bool = False,
    ) -> List[Dict[str, Any]]:
        results = self._store.query(CATEGORY, limit=limit)
        if only_with_outcomes:
            results = [r for r in results if r.get("details", {}).get("outcome")]
        return results

    def get_decisions_by_action(self, action: str, limit: int = 20) -> List[Dict[str, Any]]:
        results = self._store.query(CATEGORY, limit=100)
        return [
            r for r in results
            if r.get("details", {}).get("action") == action
        ][:limit]

    def get_success_rate(self, action: Optional[str] = None) -> float:
        results = self._store.query(CATEGORY, limit=500)
        scored = []
        for r in results:
            d = r.get("details", {})
            if d.get("outcome") in ("success", "completed"):
                if action is None or d.get("action") == action:
                    scored.append(1)
            elif d.get("outcome") in ("failure", "error", "dismissed"):
                if action is None or d.get("action") == action:
                    scored.append(0)
        if not scored:
            return 0.5
        return sum(scored) / len(scored)

    def get_confidence_trend(self, action: str, limit: int = 50) -> List[Tuple[float, float]]:
        results = self._store.query(CATEGORY, limit=limit)
        pairs = []
        for r in results:
            d = r.get("details", {})
            if d.get("action") == action:
                conf = d.get("confidence", 0.0)
                ts = d.get("timestamp", 0.0)
                pairs.append((ts, conf))
        pairs.sort(key=lambda x: x[0])
        return pairs

    def count_decisions(self, action: Optional[str] = None) -> int:
        results = self._store.query(CATEGORY, limit=1000)
        if action:
            return sum(1 for r in results if r.get("details", {}).get("action") == action)
        return len(results)


_DECISION_MEMORY: Optional[DecisionMemory] = None


def get_decision_memory() -> DecisionMemory:
    global _DECISION_MEMORY
    if _DECISION_MEMORY is None:
        _DECISION_MEMORY = DecisionMemory()
    return _DECISION_MEMORY
