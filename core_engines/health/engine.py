"""SystemHealthEngine — evaluates global system health and emits status events."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from core_engines.health.scoring import (
    HealthScoringSystem,
    HealthStatus,
    classify_health,
)

logger = logging.getLogger("rastro.health.engine")

DEFAULT_INTERVAL = 10.0


class SystemHealthEngine:
    """Central health evaluation engine.

    Collects metrics from all subsystems, computes a 0-100 health score,
    and emits health status events to the EventBus.
    """

    def __init__(self) -> None:
        self._scoring = HealthScoringSystem()
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._interval = DEFAULT_INTERVAL
        self._last_status: HealthStatus | None = None
        self._eventbus: Any = None
        self._agent_bus: Any = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="rastro-health-engine",
        )
        self._thread.start()
        logger.info("[HEALTH] Engine started (interval=%ss)", self._interval)

    def stop(self) -> None:
        self._running = False
        self._thread = None
        logger.info("[HEALTH] Engine stopped")

    def set_interval(self, interval: float) -> None:
        self._interval = max(2.0, interval)

    # ── Metrics collection ────────────────────────────────────────────

    def _collect_metrics(self) -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "eventbus_failures": 0,
            "agent_crashes": 0,
            "scheduler_latency_sec": 0,
            "db_lock_count": 0,
            "pipeline_retries": 0,
            "recovery_attempts": 0,
            "memory_percent": 0.0,
            "open_circuits": 0,
            "uptime_hours": 0,
            "total_pipelines": 0,
        }

        try:
            import psutil
            metrics["memory_percent"] = psutil.Process().memory_percent()
            metrics["uptime_hours"] = (time.time() - psutil.Process().create_time()) / 3600
        except Exception:
            pass

        try:
            from core_engines.recovery import get_recovery_engine
            engine = get_recovery_engine()
            status = engine.status()
            cb_snaps = engine.circuit_breaker_snapshots()
            metrics["open_circuits"] = sum(
                1 for s in cb_snaps.values() if s["state"] == "open"
            )
            metrics["recovery_attempts"] = len(status.get("recovery_in_progress", {}))
        except Exception:
            pass

        try:
            from core_engines.recovery import get_recovery_store
            store = get_recovery_store()
            history = store.get_recovery_history(limit=50)
            metrics["eventbus_failures"] = sum(
                1 for h in history if "eventbus" in h.get("component", "")
            )
            metrics["agent_crashes"] = sum(
                1 for h in history if "agent" in h.get("component", "")
            )
            metrics["db_lock_count"] = sum(
                1 for h in history if "db" in h.get("component", "")
            )
        except Exception:
            pass

        try:
            from core_engines.agents import get_all_agents
            agents = get_all_agents()
            metrics["agent_crashes"] += sum(
                1 for a in agents if a.tasks_failed > 0
            )
        except Exception:
            pass

        try:
            from core_engines.agents.bus import get_agent_bus
            bus = get_agent_bus()
            history = bus.get_history(limit=30)
            metrics["pipeline_retries"] = sum(
                1 for e in history
                if hasattr(e, 'event_type') and 'failed' in str(e.event_type)
            )
        except Exception:
            pass

        return metrics

    # ── Health evaluation loop ────────────────────────────────────────

    def _run_loop(self) -> None:
        while self._running:
            try:
                metrics = self._collect_metrics()
                score = self._scoring.record(metrics)
                status = classify_health(score)

                with self._lock:
                    changed = self._last_status != status
                    self._last_status = status

                event_type = {
                    HealthStatus.OK: "system:ready",
                    HealthStatus.DEGRADED: "system:degraded",
                    HealthStatus.CRITICAL: "system:error",
                    HealthStatus.RECOVERING: "system:ready",
                }.get(status, "system:ready")

                self._emit_health_event(event_type, status.value, score)

                if changed:
                    logger.info(
                        "[HEALTH] Status changed to %s (score=%.1f, trend=%s)",
                        status.value, score, self._scoring.trend(),
                    )

                logger.debug(
                    "[HEALTH] Score=%.1f status=%s metrics=%s",
                    score, status.value, metrics,
                )

            except Exception as exc:
                logger.error("[HEALTH] Engine loop error: %s", exc, exc_info=True)

            if self._running:
                time.sleep(self._interval)

    def _emit_health_event(self, event_type: str, severity: str, score: float) -> None:
        try:
            from core_engines.events.event_bus import get_event_bus
            bus = get_event_bus()
            bus.publish(
                event_type,
                source="system_health_engine",
                severity=severity,
                health_score=round(score, 1),
                trend=self._scoring.trend(),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:
            logger.debug("[HEALTH] Event emission skipped: %s", exc)

    # ── Status ────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "interval": self._interval,
                "current_score": self._scoring.current_score(),
                "current_status": self._scoring.current_status().value,
                "trend": self._scoring.trend(),
                "snapshots": len(self._scoring.history()),
            }

    def get_scoring_system(self) -> HealthScoringSystem:
        return self._scoring


_ENGINE: SystemHealthEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_system_health_engine() -> SystemHealthEngine:
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = SystemHealthEngine()
    return _ENGINE


def reset_system_health_engine() -> None:
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.stop()
    _ENGINE = None
