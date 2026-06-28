"""AutoOptimizationEngine — dynamically tunes system parameters based on metrics.

Optimizations:
- EventBus max_history: reduce on high memory, increase on low
- Scheduler interval: increase on high load, decrease on idle
- Retry backoff: increase on repeated failures
- Agent max_retries: decrease on high error rates
- Health check interval: increase on stable systems
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("rastro.optimization.engine")

OPTIMIZATION_COOLDOWN = 60.0  # seconds between optimizations


@dataclass
class OptimizationAction:
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    applied_at: str = ""


class AutoOptimizationEngine:
    """Monitors system metrics and applies automatic tuning."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._history: list[OptimizationAction] = []
        self._max_history = 100
        self._last_optimization: float = 0.0
        self._cooldown = OPTIMIZATION_COOLDOWN
        self._params: dict[str, Any] = {
            "eventbus_max_history": 500,
            "scheduler_interval_min": 30,
            "retry_backoff_base": 30,
            "agent_max_retries": 3,
            "health_check_interval": 10,
        }
        self._min_params: dict[str, float] = {
            "eventbus_max_history": 50,
            "scheduler_interval_min": 5,
            "retry_backoff_base": 5,
            "agent_max_retries": 1,
            "health_check_interval": 2,
        }
        self._max_params: dict[str, float] = {
            "eventbus_max_history": 2000,
            "scheduler_interval_min": 120,
            "retry_backoff_base": 120,
            "agent_max_retries": 10,
            "health_check_interval": 60,
        }

    def start(self) -> None:
        self._running = True
        logger.info("[OPTIMIZE] Engine started")

    def stop(self) -> None:
        self._running = False
        logger.info("[OPTIMIZE] Engine stopped")

    # ── Optimization logic ────────────────────────────────────────────

    def evaluate(self, metrics: dict[str, Any]) -> list[OptimizationAction]:
        if not self._running:
            return []

        import time
        now = time.monotonic()
        if now - self._last_optimization < self._cooldown:
            return []

        actions: list[OptimizationAction] = []

        # 1. EventBus max_history: reduce if memory high
        mem_pct = metrics.get("memory_percent", 0)
        if mem_pct > 70:
            new_val = max(
                self._min_params["eventbus_max_history"],
                int(self._params["eventbus_max_history"] * 0.5),
            )
            if new_val < self._params["eventbus_max_history"]:
                actions.append(OptimizationAction(
                    parameter="eventbus_max_history",
                    old_value=self._params["eventbus_max_history"],
                    new_value=new_val,
                    reason=f"High memory ({mem_pct:.0f}%): reducing history to {new_val}",
                ))
                self._params["eventbus_max_history"] = int(new_val)
        elif mem_pct < 30 and self._params["eventbus_max_history"] < 500:
            new_val = min(
                self._max_params["eventbus_max_history"],
                int(self._params["eventbus_max_history"] * 2),
            )
            actions.append(OptimizationAction(
                parameter="eventbus_max_history",
                old_value=self._params["eventbus_max_history"],
                new_value=new_val,
                reason=f"Low memory ({mem_pct:.0f}%): increasing history to {new_val}",
            ))
            self._params["eventbus_max_history"] = int(new_val)

        # 2. Scheduler interval: back off on failures
        recovery_attempts = metrics.get("recovery_attempts", 0)
        if recovery_attempts > 3:
            new_val = min(
                self._max_params["scheduler_interval_min"],
                self._params["scheduler_interval_min"] * 2,
            )
            actions.append(OptimizationAction(
                parameter="scheduler_interval_min",
                old_value=self._params["scheduler_interval_min"],
                new_value=new_val,
                reason=f"High recovery rate: backing off scheduler to {new_val}min",
            ))
            self._params["scheduler_interval_min"] = int(new_val)
        elif recovery_attempts == 0 and self._params["scheduler_interval_min"] > 30:
            new_val = max(
                self._min_params["scheduler_interval_min"],
                self._params["scheduler_interval_min"] // 2,
            )
            actions.append(OptimizationAction(
                parameter="scheduler_interval_min",
                old_value=self._params["scheduler_interval_min"],
                new_value=new_val,
                reason=f"Stable system: reducing scheduler interval to {new_val}min",
            ))
            self._params["scheduler_interval_min"] = int(new_val)

        # 3. Retry backoff: increase on repeated failures
        pipeline_retries = metrics.get("pipeline_retries", 0)
        if pipeline_retries > 5:
            new_val = min(
                self._max_params["retry_backoff_base"],
                self._params["retry_backoff_base"] * 1.5,
            )
            actions.append(OptimizationAction(
                parameter="retry_backoff_base",
                old_value=self._params["retry_backoff_base"],
                new_value=new_val,
                reason=f"High retry rate ({pipeline_retries}): increasing backoff to {new_val}s",
            ))
            self._params["retry_backoff_base"] = int(new_val)

        # 4. Agent max_retries: reduce on error cascades
        agent_crashes = metrics.get("agent_crashes", 0)
        if agent_crashes > 10:
            new_val = max(
                self._min_params["agent_max_retries"],
                self._params["agent_max_retries"] - 1,
            )
            actions.append(OptimizationAction(
                parameter="agent_max_retries",
                old_value=self._params["agent_max_retries"],
                new_value=new_val,
                reason=f"Agent crash cascade ({agent_crashes}): reducing retries to {new_val}",
            ))
            self._params["agent_max_retries"] = int(new_val)

        # 5. Health check interval: increase on stable systems
        open_circuits = metrics.get("open_circuits", 0)
        if open_circuits == 0 and mem_pct < 50:
            new_val = min(
                self._max_params["health_check_interval"],
                self._params["health_check_interval"] * 1.5,
            )
            actions.append(OptimizationAction(
                parameter="health_check_interval",
                old_value=self._params["health_check_interval"],
                new_value=new_val,
                reason=f"Stable system: reducing health check frequency to {new_val}s",
            ))
            self._params["health_check_interval"] = int(new_val)

        if actions:
            self._last_optimization = now
            for action in actions:
                action.applied_at = datetime.now(timezone.utc).isoformat()
                logger.info(
                    "[OPTIMIZE] %s: %s → %s (%s)",
                    action.parameter, action.old_value, action.new_value, action.reason,
                )
            with self._lock:
                self._history.extend(actions)
                if len(self._history) > self._max_history:
                    self._history[:] = self._history[-self._max_history:]

            self._emit_optimization_events(actions)

        return actions

    def _emit_optimization_events(self, actions: list[OptimizationAction]) -> None:
        for action in actions:
            try:
                from core_engines.events.event_bus import get_event_bus
                bus = get_event_bus()
                bus.publish(
                    "auto_optimization_applied",
                    parameter=action.parameter,
                    old_value=str(action.old_value),
                    new_value=str(action.new_value),
                    reason=action.reason,
                    source="optimization_engine",
                )
            except Exception as exc:
                logger.debug("[OPTIMIZE] Event emission skipped: %s", exc)

    # ── State ─────────────────────────────────────────────────────────

    def get_params(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._params)

    def get_history(self) -> list[OptimizationAction]:
        with self._lock:
            return list(self._history)

    def reset_params(self) -> None:
        with self._lock:
            self._params = {
                "eventbus_max_history": 500,
                "scheduler_interval_min": 30,
                "retry_backoff_base": 30,
                "agent_max_retries": 3,
                "health_check_interval": 10,
            }


_ENGINE: AutoOptimizationEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_optimization_engine() -> AutoOptimizationEngine:
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = AutoOptimizationEngine()
    return _ENGINE


def reset_optimization_engine() -> None:
    global _ENGINE
    _ENGINE = None
