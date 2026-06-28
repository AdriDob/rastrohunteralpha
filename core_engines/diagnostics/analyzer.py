"""DiagnosticAnalyzer — detects failure patterns and generates root cause hypotheses."""

from __future__ import annotations

import logging
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("rastro.diagnostics.analyzer")

PATTERN_WINDOW_SIZE = 200


@dataclass
class FailurePattern:
    pattern_id: str
    description: str
    frequency: int
    affected_components: list[str]
    typical_error: str
    first_seen: str
    last_seen: str
    confidence: float  # 0.0 – 1.0


@dataclass
class RootCauseHypothesis:
    component: str
    confidence: float
    evidence: list[str]
    suggested_action: str
    generated_at: str


class DiagnosticAnalyzer:
    """Analyzes failure history to detect patterns and suggest root causes.

    Features:
    - Groups identical errors to detect frequency patterns
    - Identifies components with highest failure rates
    - Detects periodic failures (every N cycles)
    - Generates root cause hypotheses
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._error_history: list[dict[str, Any]] = []
        self._max_history = PATTERN_WINDOW_SIZE

    def record_error(
        self,
        component: str,
        error_message: str,
        failure_type: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self._error_history.append({
                "component": component,
                "error_message": error_message,
                "failure_type": failure_type,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            if len(self._error_history) > self._max_history:
                self._error_history[:] = self._error_history[-self._max_history // 2:]

    # ── Pattern detection ─────────────────────────────────────────────

    def find_patterns(self) -> list[FailurePattern]:
        with self._lock:
            if not self._error_history:
                return []

            # Group by component + error message
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for entry in self._error_history:
                key = f"{entry['component']}:{entry['error_message'][:80]}"
                groups[key].append(entry)

            patterns: list[FailurePattern] = []
            for key, entries in groups.items():
                if len(entries) < 2:
                    continue
                component = entries[0]["component"]
                error = entries[0]["error_message"][:120]
                timestamps = [e["timestamp"] for e in entries]
                frequency = len(entries)
                confidence = min(1.0, frequency / 10)

                patterns.append(FailurePattern(
                    pattern_id=f"pat_{hash(key) % 100000:05d}",
                    description=(
                        f"Repeated failure in {component}: "
                        f"{frequency} occurrences in last {len(self._error_history)} events"
                    ),
                    frequency=frequency,
                    affected_components=[component],
                    typical_error=error,
                    first_seen=min(timestamps),
                    last_seen=max(timestamps),
                    confidence=confidence,
                ))

            patterns.sort(key=lambda p: p.frequency, reverse=True)
            return patterns[:20]

    def find_periodic_failures(self) -> list[FailurePattern]:
        """Detect failures that occur at regular intervals."""
        with self._lock:
            patterns = []
            components = set(e["component"] for e in self._error_history)

            for comp in components:
                comp_errors = [e for e in self._error_history if e["component"] == comp]
                if len(comp_errors) < 5:
                    continue

                # Simple periodic check: same error type occurring repeatedly
                error_types = Counter(
                    e["failure_type"] for e in comp_errors
                )
                for failure_type, count in error_types.most_common(3):
                    if count >= 3:
                        patterns.append(FailurePattern(
                            pattern_id=f"periodic_{comp}_{failure_type}",
                            description=(
                                f"Periodic {failure_type} in {comp}: "
                                f"{count} occurrences"
                            ),
                            frequency=count,
                            affected_components=[comp],
                            typical_error=failure_type,
                            first_seen=comp_errors[0]["timestamp"],
                            last_seen=comp_errors[-1]["timestamp"],
                            confidence=min(0.8, count / 8),
                        ))

            patterns.sort(key=lambda p: p.frequency, reverse=True)
            return patterns[:10]

    def most_failing_components(self, top_n: int = 5) -> list[dict[str, Any]]:
        with self._lock:
            counts: Counter = Counter(e["component"] for e in self._error_history)
            return [
                {"component": comp, "failures": count}
                for comp, count in counts.most_common(top_n)
            ]

    # ── Root cause analysis ───────────────────────────────────────────

    def generate_hypotheses(self) -> list[RootCauseHypothesis]:
        patterns = self.find_patterns()
        hypotheses: list[RootCauseHypothesis] = []

        for pattern in patterns[:5]:
            comp = pattern.affected_components[0]

            if "eventbus" in comp or "event_bus" in comp:
                hypotheses.append(RootCauseHypothesis(
                    component=comp,
                    confidence=min(1.0, pattern.confidence + 0.1),
                    evidence=[
                        pattern.typical_error,
                        f"{pattern.frequency} eventbus failures recorded",
                        f"First seen: {pattern.first_seen}",
                    ],
                    suggested_action="reset_event_bus",
                    generated_at=datetime.now(timezone.utc).isoformat(),
                ))
            elif "agent" in comp.lower():
                hypotheses.append(RootCauseHypothesis(
                    component=comp,
                    confidence=min(1.0, pattern.confidence + 0.05),
                    evidence=[
                        pattern.typical_error,
                        f"{pattern.frequency} failures in agent {comp}",
                    ],
                    suggested_action=f"restart_agent:{comp}",
                    generated_at=datetime.now(timezone.utc).isoformat(),
                ))
            elif "scheduler" in comp.lower():
                hypotheses.append(RootCauseHypothesis(
                    component=comp,
                    confidence=pattern.confidence,
                    evidence=[
                        pattern.typical_error,
                        f"Scheduler failed {pattern.frequency} times",
                    ],
                    suggested_action="restart_scheduler",
                    generated_at=datetime.now(timezone.utc).isoformat(),
                ))
            elif "db" in comp.lower() or "database" in comp.lower():
                hypotheses.append(RootCauseHypothesis(
                    component=comp,
                    confidence=pattern.confidence,
                    evidence=[
                        pattern.typical_error,
                        f"Database errors: {pattern.frequency} occurrences",
                    ],
                    suggested_action="reopen_db_connection",
                    generated_at=datetime.now(timezone.utc).isoformat(),
                ))
            else:
                hypotheses.append(RootCauseHypothesis(
                    component=comp,
                    confidence=pattern.confidence * 0.5,
                    evidence=[
                        pattern.typical_error,
                        f"Unknown component: {pattern.frequency} failures",
                    ],
                    suggested_action="generic_recovery",
                    generated_at=datetime.now(timezone.utc).isoformat(),
                ))

        return hypotheses

    def diagnose(self, error_message: str, component: str) -> RootCauseHypothesis | None:
        """Quick diagnosis for a single error."""
        self.record_error(component, error_message)
        hypotheses = self.generate_hypotheses()
        for h in hypotheses:
            if h.component == component or component in h.component:
                return h
        return None

    def clear(self) -> None:
        with self._lock:
            self._error_history.clear()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_errors": len(self._error_history),
                "unique_components": len(set(e["component"] for e in self._error_history)),
                "patterns_found": len(self.find_patterns()),
                "hypotheses_generated": len(self.generate_hypotheses()),
            }


_ANALYZER: DiagnosticAnalyzer | None = None
_ANALYZER_LOCK = threading.Lock()


def get_diagnostic_analyzer() -> DiagnosticAnalyzer:
    global _ANALYZER
    if _ANALYZER is None:
        with _ANALYZER_LOCK:
            if _ANALYZER is None:
                _ANALYZER = DiagnosticAnalyzer()
    return _ANALYZER


def reset_diagnostic_analyzer() -> None:
    global _ANALYZER
    _ANALYZER = None
