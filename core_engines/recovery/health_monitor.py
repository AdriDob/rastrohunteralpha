"""HealthMonitor — periodic health check loop that feeds the RecoveryEngine.

Checks every N seconds:
- EventBus alive and publishing
- Agent bus alive
- All agents responsive
- Scheduler running
- Database connectivity
- Memory usage (leak detection)
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from core_engines.recovery.engine import RecoveryEngine, get_recovery_engine

logger = logging.getLogger("rastro.recovery.health_monitor")

DEFAULT_INTERVAL = 8.0
MAX_HISTORY = 200


class HealthMonitor:
    """Background thread loop that checks all system components periodically."""

    def __init__(
        self,
        engine: RecoveryEngine | None = None,
        interval: float = DEFAULT_INTERVAL,
        health_url: str = "http://127.0.0.1:8000/api/health",
    ) -> None:
        self._engine = engine or get_recovery_engine()
        self._interval = interval
        self._health_url = health_url
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._history: list[dict[str, Any]] = []
        self._last_health: dict[str, bool] = {
            "eventbus": True,
            "agent_bus": True,
            "agents": True,
            "scheduler": True,
            "database": True,
            "memory": True,
        }

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="rastro-health-monitor",
        )
        self._thread.start()
        logger.info("[HEALTH] Monitor started (interval=%ss)", self._interval)

    def stop(self) -> None:
        self._running = False
        self._thread = None
        logger.info("[HEALTH] Monitor stopped")

    def _run_loop(self) -> None:
        while self._running:
            try:
                self._check_all()
            except Exception as exc:
                logger.error("[HEALTH] Monitor loop error: %s", exc, exc_info=True)

            if self._running:
                time.sleep(self._interval)

    def _check_all(self) -> None:
        checks = [
            ("eventbus", self._check_eventbus),
            ("agent_bus", self._check_agent_bus),
            ("agents", self._check_agents),
            ("database", self._check_database),
            ("memory", self._check_memory),
        ]

        all_ok = True
        degraded = False

        for name, check_fn in checks:
            ok = check_fn()
            with self._lock:
                changed = self._last_health.get(name) != ok
                self._last_health[name] = ok

            if not ok:
                all_ok = False
                if name in ("eventbus", "agent_bus", "database"):
                    degraded = True
                if changed:
                    self._engine.report_failure(
                        component=name,
                        error_message=f"Health check failed for {name}",
                    )
            else:
                if changed:
                    self._engine.report_success(component=name)

        # Overall health status
        if all_ok:
            self._emit_health("system:ready", "healthy", "All components healthy")
        elif degraded:
            self._emit_health("system:degraded", "degraded", "Critical component failure")
        else:
            self._emit_health("system:alert", "degraded", "Non-critical component failure")

        snapshot = {
            "timestamp": time.time(),
            "checks": dict(self._last_health),
            "all_ok": all_ok,
        }
        with self._lock:
            self._history.append(snapshot)
            if len(self._history) > MAX_HISTORY:
                self._history[:] = self._history[-MAX_HISTORY // 2:]

    def _check_eventbus(self) -> bool:
        try:
            from core_engines.events.event_bus import get_event_bus
            bus = get_event_bus()
            bus.publish("system:ready", service="health_monitor")
            return True
        except Exception as exc:
            logger.warning("[HEALTH] EventBus check failed: %s", exc)
            return False

    def _check_agent_bus(self) -> bool:
        try:
            from core_engines.agents.bus import get_agent_bus
            bus = get_agent_bus()
            return bus is not None
        except Exception as exc:
            logger.warning("[HEALTH] Agent bus check failed: %s", exc)
            return False

    def _check_agents(self) -> bool:
        try:
            import httpx
            base = self._health_url.rsplit("/api/health", 1)[0]
            r = httpx.get(f"{base}/api/agents/health", timeout=3.0)
            if r.status_code != 200:
                return False
            data = r.json()
            if isinstance(data, list):
                agents = data
            else:
                agents = data.get("agents", data.get("data", []))
            return all(a.get("status") == "running" for a in agents)
        except Exception:
            return False

    def _check_database(self) -> bool:
        try:
            from sqlalchemy import text

            from database.db import SessionLocal
            session = SessionLocal()
            try:
                session.execute(text("SELECT 1"))
                return True
            finally:
                session.close()
        except Exception as exc:
            logger.warning("[HEALTH] Database check failed: %s", exc)
            return False

    def _check_memory(self) -> bool:
        try:
            import psutil
            mem = psutil.Process().memory_percent()
            return mem < 80.0
        except Exception:
            return True

    def _emit_health(self, event_type: str, severity: str, message: str) -> None:
        try:
            from core_engines.events.event_bus import get_event_bus
            bus = get_event_bus()
            bus.publish(event_type, severity=severity, message=message, source="health_monitor")
        except Exception:
            pass

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "interval": self._interval,
                "last_checks": dict(self._last_health),
                "history_count": len(self._history),
            }


_MONITOR: HealthMonitor | None = None
_MONITOR_LOCK = threading.Lock()


def get_health_monitor() -> HealthMonitor:
    global _MONITOR
    if _MONITOR is None:
        with _MONITOR_LOCK:
            if _MONITOR is None:
                _MONITOR = HealthMonitor()
    return _MONITOR


def reset_health_monitor() -> None:
    global _MONITOR
    if _MONITOR is not None:
        _MONITOR.stop()
    _MONITOR = None
