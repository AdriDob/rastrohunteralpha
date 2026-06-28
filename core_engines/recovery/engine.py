"""RecoveryEngine — central coordinator for detecting, diagnosing, and recovering from failures.

Integrates with:
- EventBus (system events) for event-driven detection
- AgentBus for agent lifecycle events
- Watchdog for periodic health monitoring
- CircuitBreaker for protection against infinite loops
- RecoveryStore for persistence
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from core_engines.recovery.circuit_breaker import CircuitBreakerRegistry
from core_engines.recovery.healing_rules import (
    FailureType,
    HealingRule,
    classify_failure,
    get_rule,
)
from core_engines.recovery.persistence import get_recovery_store

logger = logging.getLogger("rastro.recovery.engine")

# Maximum duration (seconds) for a single recovery action before considered hung
RECOVERY_TIMEOUT = 30.0


class RecoveryEngine:
    """Orchestrates failure detection, diagnosis, and recovery."""

    def __init__(self) -> None:
        self._store = get_recovery_store()
        self._breakers = CircuitBreakerRegistry()
        self._running = False
        self._lock = threading.Lock()
        self._recovery_in_progress: dict[str, float] = {}
        self._on_recovery_callbacks: dict[str, list[Callable[[str, str], None]]] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        logger.info("[RECOVERY] Engine started")

    def stop(self) -> None:
        self._running = False
        with self._lock:
            self._recovery_in_progress.clear()
        logger.info("[RECOVERY] Engine stopped")

    # ── Failure detection and diagnosis ───────────────────────────────

    def report_failure(
        self,
        component: str,
        error_message: str,
        failure_type: FailureType | None = None,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Report a component failure to the engine.

        Returns True if recovery was initiated, False if circuit breaker prevents it.
        """
        if not self._running:
            logger.warning("[RECOVERY] Engine not running, ignoring failure: %s/%s", component, error_message[:80])
            return False

        if failure_type is None:
            failure_type = classify_failure(error_message, component)

        rule = get_rule(failure_type)
        if rule is None:
            logger.warning("[RECOVERY] No healing rule for %s/%s", component, failure_type.value)
            self._store.record_recovery(
                component=component,
                failure_type=failure_type.value,
                recovery_action="none",
                status="skipped",
                details=f"No rule for {failure_type.value}: {error_message[:200]}",
            )
            return False

        with self._lock:
            if component in self._recovery_in_progress:
                elapsed = time.monotonic() - self._recovery_in_progress[component]
                if elapsed < RECOVERY_TIMEOUT:
                    logger.warning(
                        "[RECOVERY] Recovery already in progress for %s (%.0fs elapsed)",
                        component, elapsed,
                    )
                    return False
                else:
                    logger.warning("[RECOVERY] Stale recovery detected for %s, allowing new attempt", component)
                    del self._recovery_in_progress[component]

        cb = self._breakers.get(component)
        if rule.requires_circuit_breaker:
            if not cb.can_attempt_recovery():
                snap = cb.snapshot()
                logger.error(
                    "[RECOVERY] Circuit breaker OPEN for %s (state=%s, failures=%d) — recovery blocked",
                    component, snap["state"], snap["failure_count"],
                )
                self._store.record_recovery(
                    component=component,
                    failure_type=failure_type.value,
                    recovery_action=rule.recovery_action,
                    status="blocked",
                    details=f"Circuit breaker {snap['state']}, {snap['failure_count']} failures",
                )
                return False

        self._execute_recovery(component, failure_type, rule, error_message, details)
        return True

    def report_success(self, component: str) -> None:
        """Report successful operation — reset circuit breaker."""
        cb = self._breakers.get(component)
        cb.record_success()
        self._store.record_recovery(
            component=component,
            failure_type="none",
            recovery_action="acknowledged",
            status="success",
        )
        with self._lock:
            self._recovery_in_progress.pop(component, None)

    # ── Recovery execution ────────────────────────────────────────────

    def _execute_recovery(
        self,
        component: str,
        failure_type: FailureType,
        rule: HealingRule,
        error_message: str,
        details: dict[str, Any] | None,
    ) -> None:
        with self._lock:
            self._recovery_in_progress[component] = time.monotonic()

        logger.warning(
            "[RECOVERY] %s on %s: %s (action=%s)",
            failure_type.value, component, error_message[:120], rule.recovery_action,
        )

        t0 = time.monotonic()
        success = False
        error_detail = ""

        try:
            self._emit_recovery_event("recovery:started", component, failure_type.value, rule.recovery_action)
            success, error_detail = self._run_action(rule.recovery_action, component, details)
            elapsed = (time.monotonic() - t0) * 1000
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            success = False
            error_detail = str(exc)
            logger.error("[RECOVERY] Action %s failed with exception: %s", rule.recovery_action, exc)

        cb = self._breakers.get(component)
        if success:
            cb.record_success()
            self._store.record_recovery(
                component=component,
                failure_type=failure_type.value,
                recovery_action=rule.recovery_action,
                status="success",
                details=error_detail or "OK",
                duration_ms=elapsed,
            )
            self._emit_recovery_event("recovery:success", component, failure_type.value, rule.recovery_action)
            logger.info("[RECOVERY] %s recovered via %s (%.0fms)", component, rule.recovery_action, elapsed)
        else:
            cb.record_failure()
            self._store.record_recovery(
                component=component,
                failure_type=failure_type.value,
                recovery_action=rule.recovery_action,
                status="failed",
                details=error_detail or "Unknown error",
                duration_ms=elapsed,
            )
            self._emit_recovery_event("recovery:failed", component, failure_type.value, rule.recovery_action)
            logger.error("[RECOVERY] %s recovery FAILED via %s (%.0fms): %s",
                         component, rule.recovery_action, elapsed, error_detail)

        with self._lock:
            self._recovery_in_progress.pop(component, None)

    def _run_action(
        self, action: str, component: str, details: dict[str, Any] | None
    ) -> tuple[bool, str]:
        actions = {
            "reset_event_bus": self._action_reset_event_bus,
            "restart_agent_bus": self._action_restart_agent_bus,
            "restart_agent": self._action_restart_agent,
            "restart_scheduler": self._action_restart_scheduler,
            "restore_last_valid_state": self._action_restore_pipeline,
            "retry_pipeline": self._action_retry_pipeline,
            "reopen_db_connection": self._action_reopen_db,
            "trim_memory_history": self._action_trim_memory,
            "reset_memory_store": self._action_reset_memory,
            "restart_watchdog": self._action_restart_watchdog,
            "restart_api_server": self._action_restart_api,
        }
        handler = actions.get(action)
        if handler is None:
            return False, f"Unknown recovery action: {action}"
        return handler(component, details)

    # ── Concrete recovery actions ────────────────────────────────────

    def _action_reset_event_bus(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            from core_engines.events.event_bus import get_event_bus
            bus = get_event_bus()
            bus.clear_history()
            bus.publish("system:boot:complete", service="recovery", component=component)
            return True, "Event bus reset and re-published system:boot:complete"
        except Exception as exc:
            return False, str(exc)

    def _action_restart_agent_bus(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            from core_engines.agents.bus import reset_agent_bus
            reset_agent_bus()
            from core_engines.agents.bus import get_agent_bus
            get_agent_bus()
            return True, "Agent bus reset and re-initialized"
        except Exception as exc:
            return False, str(exc)

    def _action_restart_agent(self, component: str, details: dict | None) -> tuple[bool, str]:
        agent_id = (details or {}).get("agent_id", component)
        try:
            from core_engines.agents import get_all_agents
            from core_engines.agents.types import AgentId
            agents = get_all_agents()
            for agent in agents:
                if agent.agent_id.value == agent_id or agent.agent_id == AgentId(agent_id):
                    agent.stop()
                    agent.start()
                    return True, f"Agent {agent_id} restarted"
            return False, f"Agent {agent_id} not found"
        except Exception as exc:
            return False, str(exc)

    def _action_restart_all_agents(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            from core_engines.agents import restart_all_agents
            agents = restart_all_agents()
            return True, f"All {len(agents)} agents restarted"
        except Exception as exc:
            return False, str(exc)

    def _action_restart_scheduler(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            import httpx

            from core_engines.settings.service import get_setting
            base = get_setting("rastro.api_url", "http://127.0.0.1:8000")
            r = httpx.post(f"{base}/api/scheduler/restart", timeout=5.0)
            if r.status_code == 200:
                return True, "Scheduler restart requested via API"
            return False, f"Scheduler restart returned HTTP {r.status_code}"
        except Exception as exc:
            return False, str(exc)

    def _action_restore_pipeline(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            from core_engines.agents.coordinator import get_coordinator
            coord = get_coordinator()
            coord._active_pipelines.clear()
            return True, "Pipeline state cleared, will reload from DB on next access"
        except Exception as exc:
            return False, str(exc)

    def _action_retry_pipeline(self, component: str, details: dict | None) -> tuple[bool, str]:
        pipeline_id = (details or {}).get("pipeline_id", component)
        try:
            from core_engines.agents.bus import get_agent_bus
            from core_engines.agents.types import EventType
            bus = get_agent_bus()
            from core_engines.agents.types import AgentEvent
            bus.publish(AgentEvent(
                event_type=EventType.PIPELINE_START,
                source="recovery_engine",
                target="coordinator",
                correlation_id=pipeline_id,
                payload={"pipeline_id": pipeline_id, "recovered": True},
            ))
            return True, f"Pipeline {pipeline_id[:8]} retry requested"
        except Exception as exc:
            return False, str(exc)

    def _action_reopen_db(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            from sqlalchemy import text

            from database.db import engine
            with engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA busy_timeout=5000"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
                conn.commit()
            return True, "Database connection re-opened with WAL mode and busy_timeout"
        except Exception as exc:
            return False, str(exc)

    def _action_trim_memory(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            from core_engines.intelligence.event_system import get_event_system
            es = get_event_system()
            es.clear()
            from core_engines.events.event_bus import get_event_bus
            eb = get_event_bus()
            eb.clear_history()
            return True, "Event system and event bus history trimmed"
        except Exception as exc:
            return False, str(exc)

    def _action_reset_memory(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            from core_engines.memory.memory_store import get_memory_store
            store = get_memory_store()
            store.clear()
            return True, "Memory store reset"
        except Exception as exc:
            return False, str(exc)

    def _action_restart_watchdog(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            from desktop.watchdog import get_watchdog
            wd = get_watchdog()
            if wd:
                wd.stop()
                wd.start()
                return True, "Watchdog restarted"
            return False, "No watchdog instance found"
        except Exception as exc:
            return False, str(exc)

    def _action_restart_api(self, component: str, details: dict | None) -> tuple[bool, str]:
        try:
            import httpx
            base = (details or {}).get("api_url", "http://127.0.0.1:8000")
            r = httpx.post(f"{base}/api/system/restart", timeout=5.0)
            if r.status_code == 200:
                return True, "API restart requested"
            return False, f"API restart returned HTTP {r.status_code}"
        except Exception as exc:
            return False, str(exc)

    # ── Event emission ────────────────────────────────────────────────

    def _emit_recovery_event(self, event_type: str, component: str, failure: str, action: str) -> None:
        try:
            from core_engines.events.event_bus import get_event_bus
            bus = get_event_bus()
            bus.publish(
                event_type,
                component=component,
                failure_type=failure,
                recovery_action=action,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:
            logger.debug("[RECOVERY] Event emission skipped: %s", exc)

    # ── Status ────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "circuit_breakers": self._breakers.all_snapshots(),
            "recovery_in_progress": dict(self._recovery_in_progress),
        }

    def circuit_breaker_snapshots(self) -> dict[str, dict[str, Any]]:
        return self._breakers.all_snapshots()


_ENGINE: RecoveryEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_recovery_engine() -> RecoveryEngine:
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = RecoveryEngine()
    return _ENGINE


def reset_recovery_engine() -> None:
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.stop()
    _ENGINE = None
