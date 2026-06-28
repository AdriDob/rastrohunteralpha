"""AutonomousModeEngine — AUTONOMOUS+ mode orchestrator.

Aggregates all intelligence layers (health, diagnostics, prediction, optimization)
to make autonomous decisions about system management.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("rastro.autonomous.engine")

AUTONOMOUS_INTERVAL = 15.0


@dataclass
class AutonomousDecision:
    decision_type: str
    confidence: float
    reason: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


class AutonomousModeEngine:
    """Orchestrates all RC7 intelligence layers in AUTONOMOUS+ mode.

    Cycle:
    1. Collect metrics from all subsystems
    2. Evaluate health score
    3. Run diagnostics on error history
    4. Predict future failures
    5. Apply auto-optimizations
    6. Take autonomous actions if needed
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._enabled = False
        self._thread: threading.Thread | None = None
        self._interval = AUTONOMOUS_INTERVAL
        self._decisions: list[AutonomousDecision] = []
        self._max_history = 200
        self._paused_pipelines: set[str] = set()

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_cycle, daemon=True, name="rastro-autonomous",
        )
        self._thread.start()
        logger.info("[AUTO+] Engine started (interval=%ss, enabled=%s)", self._interval, self._enabled)

    def stop(self) -> None:
        self._running = False
        self._thread = None
        logger.info("[AUTO+] Engine stopped")

    def enable(self) -> None:
        self._enabled = True
        logger.info("[AUTO+] AUTONOMOUS+ mode enabled")

    def disable(self) -> None:
        self._enabled = False
        logger.info("[AUTO+] AUTONOMOUS+ mode disabled")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    # ── Main autonomous cycle ─────────────────────────────────────────

    def _run_cycle(self) -> None:
        while self._running:
            try:
                if self._enabled:
                    self._autonomous_cycle()
            except Exception as exc:
                logger.error("[AUTO+] Cycle error: %s", exc, exc_info=True)

            if self._running:
                time.sleep(self._interval)

    def _autonomous_cycle(self) -> None:
        metrics = self._collect_metrics()
        decisions: list[AutonomousDecision] = []

        # 1. Health check
        try:
            from core_engines.health import get_system_health_engine
            health = get_system_health_engine()
            health_status = health.status()
            health_score = health_status.get("current_score", 100)
            if health_score < 50:
                decisions.append(AutonomousDecision(
                    decision_type="degrade_load",
                    confidence=0.7,
                    reason=f"Health score {health_score:.0f} below 50: degrading load",
                    action="degrade_pipeline_throughput",
                ))
        except Exception as exc:
            logger.debug("[AUTO+] Health check skipped: %s", exc)

        # 2. Diagnostics
        try:
            from core_engines.diagnostics import get_diagnostic_analyzer
            analyzer = get_diagnostic_analyzer()
            patterns = analyzer.find_patterns()
            if patterns and patterns[0].confidence > 0.5:
                decisions.append(AutonomousDecision(
                    decision_type="root_cause_detected",
                    confidence=patterns[0].confidence,
                    reason=patterns[0].description,
                    action="apply_recovery",
                    parameters={"pattern_id": patterns[0].pattern_id},
                ))
        except Exception as exc:
            logger.debug("[AUTO+] Diagnostics skipped: %s", exc)

        # 3. Failure prediction
        try:
            from core_engines.predictor import get_failure_predictor
            predictor = get_failure_predictor()
            predictions = predictor.predict()
            for pred in predictions[:3]:
                if pred.risk_level.value == "high_risk":
                    decisions.append(AutonomousDecision(
                        decision_type="preventive_action",
                        confidence=pred.probability,
                        reason=f"High risk failure predicted in {pred.component} ({pred.probability:.0%})",
                        action=pred.recommended_action or "inspect_component",
                        parameters={
                            "component": pred.component,
                            "predicted_type": pred.predicted_failure_type,
                        },
                    ))
        except Exception as exc:
            logger.debug("[AUTO+] Prediction skipped: %s", exc)

        # 4. Auto-optimization
        try:
            from core_engines.optimization import get_optimization_engine
            optimizer = get_optimization_engine()
            optimizations = optimizer.evaluate(metrics)
            for opt in optimizations:
                decisions.append(AutonomousDecision(
                    decision_type="parameter_tuning",
                    confidence=0.8,
                    reason=opt.reason,
                    action=f"adjust_{opt.parameter}",
                    parameters={
                        "parameter": opt.parameter,
                        "old_value": opt.old_value,
                        "new_value": opt.new_value,
                    },
                ))
        except Exception as exc:
            logger.debug("[AUTO+] Optimization skipped: %s", exc)

        # 5. Take actions
        for decision in decisions:
            if decision.confidence >= 0.6:
                self._execute_decision(decision)

        # Log and store decisions
        if decisions:
            with self._lock:
                for d in decisions:
                    d.timestamp = datetime.now(timezone.utc).isoformat()
                self._decisions.extend(decisions)
                if len(self._decisions) > self._max_history:
                    self._decisions[:] = self._decisions[-self._max_history:]

            self._emit_decision_events(decisions)

    # ── Metrics ───────────────────────────────────────────────────────

    def _collect_metrics(self) -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "memory_percent": 0,
            "recovery_attempts": 0,
            "pipeline_retries": 0,
            "agent_crashes": 0,
            "open_circuits": 0,
        }

        try:
            import psutil
            metrics["memory_percent"] = psutil.Process().memory_percent()
        except Exception:
            pass

        try:
            from core_engines.recovery import get_recovery_engine
            engine = get_recovery_engine()
            status = engine.status()
            metrics["recovery_attempts"] = len(status.get("recovery_in_progress", {}))
            cb_snaps = status.get("circuit_breakers", {})
            metrics["open_circuits"] = sum(
                1 for s in cb_snaps.values() if s.get("state") == "open"
            )
        except Exception:
            pass

        try:
            from core_engines.agents import get_all_agents
            agents = get_all_agents()
            metrics["agent_crashes"] = sum(
                1 for a in agents if a.tasks_failed > 5
            )
        except Exception:
            pass

        return metrics

    # ── Decision execution ────────────────────────────────────────────

    def _execute_decision(self, decision: AutonomousDecision) -> None:
        logger.info(
            "[AUTO+] Executing decision: %s (confidence=%.2f, action=%s)",
            decision.decision_type, decision.confidence, decision.action,
        )

        if decision.action in ("degrade_pipeline_throughput",):
            self._degrade_load()

        elif decision.action == "apply_recovery":
            self._apply_recovery(decision.parameters)

        elif decision.action.startswith("inspect_component"):
            component = decision.parameters.get("component", "unknown")
            logger.info("[AUTO+] Inspection requested for %s", component)

    def _degrade_load(self) -> None:
        logger.warning("[AUTO+] Degrading system load: pausing non-critical pipelines")
        try:
            from core_engines.agents import get_all_agents
            from core_engines.agents.bus import get_agent_bus
            from core_engines.agents.types import AgentEvent, EventType
            bus = get_agent_bus()
            for agent in get_all_agents():
                if agent.agent_id.value in ("research", "exploit"):
                    bus.publish(AgentEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        source="autonomous_engine",
                        target=agent.agent_id,
                        payload={
                            "action": "pause",
                            "reason": "System degradation: reducing load",
                        },
                    ))
        except Exception as exc:
            logger.error("[AUTO+] Load degradation failed: %s", exc)

    def _apply_recovery(self, params: dict[str, Any]) -> None:
        try:
            from core_engines.recovery import get_recovery_engine
            engine = get_recovery_engine()
            engine.report_failure(
                component="autonomous",
                error_message=f"Autonomous recovery: {params.get('pattern_id', 'unknown')}",
                details=params,
            )
        except Exception as exc:
            logger.error("[AUTO+] Recovery trigger failed: %s", exc)

    def _emit_decision_events(self, decisions: list[AutonomousDecision]) -> None:
        for decision in decisions:
            try:
                from core_engines.events.event_bus import get_event_bus
                bus = get_event_bus()
                bus.publish(
                    "auto_optimization_applied" if decision.decision_type == "parameter_tuning"
                    else "anomaly_detected",
                    decision_type=decision.decision_type,
                    confidence=decision.confidence,
                    reason=decision.reason,
                    action=decision.action,
                    source="autonomous_engine",
                )
            except Exception:
                pass

    # ── State ─────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "enabled": self._enabled,
                "interval": self._interval,
                "decisions_taken": len(self._decisions),
                "paused_pipelines": list(self._paused_pipelines),
            }

    def get_recent_decisions(self, limit: int = 20) -> list[AutonomousDecision]:
        with self._lock:
            return list(self._decisions[-limit:])


_ENGINE: AutonomousModeEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_autonomous_engine() -> AutonomousModeEngine:
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = AutonomousModeEngine()
    return _ENGINE


def reset_autonomous_engine() -> None:
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.stop()
    _ENGINE = None
