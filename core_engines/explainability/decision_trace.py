"""DecisionTrace — full provenance trace of a single decision from signal to action.

A trace captures:
1. Input signals that triggered the decision
2. Processing steps (scoring, ranking, filtering)
3. Context at decision time
4. The decision itself
5. The outcome (recorded later)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("rastro.explainability.trace")


@dataclass
class TraceStep:
    name: str
    input: Any = None
    output: Any = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "input": self.input,
            "output": self.output,
            "duration_ms": round(self.duration_ms, 2),
            "metadata": self.metadata,
        }


@dataclass
class DecisionTrace:
    trace_id: str
    decision_id: str
    action: str
    steps: list[TraceStep] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    outcome: str | None = None
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def add_step(self, name: str, input: Any = None, output: Any = None, duration_ms: float = 0.0, metadata: dict[str, Any] | None = None) -> None:
        self.steps.append(TraceStep(
            name=name,
            input=input,
            output=output,
            duration_ms=duration_ms,
            metadata=metadata or {},
        ))

    def complete(self, outcome: str = "completed") -> None:
        self.completed_at = time.time()
        self.outcome = outcome

    @property
    def total_duration_ms(self) -> float:
        return sum(s.duration_ms for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "decision_id": self.decision_id,
            "action": self.action,
            "steps": [s.to_dict() for s in self.steps],
            "context": self.context,
            "outcome": self.outcome,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": round(self.total_duration_ms, 2),
        }


class TraceCollector:
    """Collects and stores decision traces for full auditability."""

    MAX_TRACES = 500

    def __init__(self) -> None:
        self._traces: dict[str, DecisionTrace] = {}

    def start_trace(self, decision_id: str, action: str, context: dict[str, Any] | None = None) -> DecisionTrace:
        trace = DecisionTrace(
            trace_id=f"trace-{decision_id}",
            decision_id=decision_id,
            action=action,
            context=context or {},
        )
        self._traces[trace.trace_id] = trace
        if len(self._traces) > self.MAX_TRACES:
            oldest = min(self._traces.keys(), key=lambda k: self._traces[k].started_at)
            del self._traces[oldest]
        return trace

    def get_trace(self, trace_id: str) -> DecisionTrace | None:
        return self._traces.get(trace_id)

    def get_trace_by_decision(self, decision_id: str) -> DecisionTrace | None:
        for trace in self._traces.values():
            if trace.decision_id == decision_id:
                return trace
        return None

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        sorted_traces = sorted(
            self._traces.values(),
            key=lambda t: t.started_at,
            reverse=True,
        )
        return [t.to_dict() for t in sorted_traces[:limit]]

    def list_by_action(self, action: str, limit: int = 10) -> list[dict[str, Any]]:
        matching = [t for t in self._traces.values() if t.action == action]
        matching.sort(key=lambda t: t.started_at, reverse=True)
        return [t.to_dict() for t in matching[:limit]]

    def count(self) -> int:
        return len(self._traces)


_TRACE_COLLECTOR: TraceCollector | None = None


def get_decision_trace() -> TraceCollector:
    global _TRACE_COLLECTOR
    if _TRACE_COLLECTOR is None:
        _TRACE_COLLECTOR = TraceCollector()
    return _TRACE_COLLECTOR
