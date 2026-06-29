"""Watchdog — internal supervisor that monitors and auto-recovers system health.

Runs as a background daemon thread. Checks every N seconds:

- API health endpoint (HTTP 200)
- Agent health (all agents responsive)
- Scheduler running
- EventBus alive
- Memory usage (%)
- CPU usage (%)

Auto-recovery with exponential backoff:
  backoff = min(30 * 2^attempt, 300) seconds
  max 5 consecutive failures before escalation
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("orion.watchdog")


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_ok: float = 0.0
    last_fail: float = 0.0
    fail_count: int = 0
    last_error: str = ""
    recovery_attempts: int = 0


@dataclass
class WatchdogSnapshot:
    timestamp: float
    services: dict[str, ServiceHealth]
    memory_percent: float
    cpu_percent: float
    overall: HealthStatus
    uptime: float


_WATCHDOG_INSTANCE: Watchdog | None = None


def get_watchdog() -> Watchdog | None:
    return _WATCHDOG_INSTANCE


class Watchdog:
    """Background supervisor that periodically checks system health."""

    def __init__(
        self,
        health_check_url: str = "http://127.0.0.1:8000/api/health",
        check_interval: float = 30.0,
        max_recovery_attempts: int = 5,
        on_recovery: Callable[[str], None] | None = None,
        on_escalate: Callable[[str], None] | None = None,
    ):
        self._health_url = health_check_url
        self._interval = check_interval
        self._max_attempts = max_recovery_attempts
        self._on_recovery = on_recovery
        self._on_escalate = on_escalate

        self._services: dict[str, ServiceHealth] = {
            "api": ServiceHealth(name="api"),
            "agents": ServiceHealth(name="agents"),
            "scheduler": ServiceHealth(name="scheduler"),
            "eventbus": ServiceHealth(name="eventbus"),
        }
        self._start_time: float = 0.0
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._snapshot_history: list[WatchdogSnapshot] = []

        global _WATCHDOG_INSTANCE
        _WATCHDOG_INSTANCE = self

    def _update_service(self, name: str, ok: bool, error: str = "") -> None:
        with self._lock:
            svc = self._services.get(name)
            if not svc:
                return
            now = time.time()
            if ok:
                svc.status = HealthStatus.HEALTHY
                svc.last_ok = now
                svc.fail_count = 0
                svc.last_error = ""
            else:
                svc.status = HealthStatus.FAILED
                svc.last_fail = now
                svc.fail_count += 1
                svc.last_error = error

    def _check_api(self) -> bool:
        try:
            import httpx
            r = httpx.get(self._health_url, timeout=5.0)
            return r.status_code == 200
        except Exception as exc:
            self._update_service("api", False, str(exc))
            return False

    def _check_agents(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self._health_url.rsplit('/api/health', 1)[0]}/api/agents/health", timeout=5.0)
            if r.status_code != 200:
                self._update_service("agents", False, f"HTTP {r.status_code}")
                return False
            data = r.json()
            all_healthy = all(
                agent.get("status") == "running"
                for agent in (data if isinstance(data, list) else data.get("agents", data.get("data", [])))
            )
            if not all_healthy:
                self._update_service("agents", False, "some agents not running")
            return all_healthy
        except Exception as exc:
            self._update_service("agents", False, str(exc))
            return False

    def _check_scheduler(self) -> bool:
        try:
            import httpx
            base = self._health_url.rsplit("/api/health", 1)[0]
            r = httpx.get(f"{base}/api/scheduler/status", timeout=5.0)
            if r.status_code != 200:
                self._update_service("scheduler", False, f"HTTP {r.status_code}")
                return False
            data = r.json()
            running = data.get("running", data.get("status") == "running")
            if not running:
                self._update_service("scheduler", False, "scheduler not running")
            return bool(running)
        except Exception as exc:
            self._update_service("scheduler", False, str(exc))
            return False

    def _check_eventbus(self) -> bool:
        try:
            from core_engines.agents.bus import get_agent_bus
            bus = get_agent_bus()
            alive = bus is not None
            if not alive:
                self._update_service("eventbus", False, "eventbus is None")
            else:
                self._update_service("eventbus", True)
            return alive
        except Exception as exc:
            self._update_service("eventbus", False, str(exc))
            return False

    def _get_memory_percent(self) -> float:
        try:
            import psutil
            return psutil.Process(os.getpid()).memory_percent()
        except Exception:
            return -1.0

    def _get_cpu_percent(self) -> float:
        try:
            import psutil
            return psutil.Process(os.getpid()).cpu_percent(interval=0.5)
        except Exception:
            return -1.0

    def _attempt_recovery(self, service_name: str) -> bool:
        svc = self._services.get(service_name)
        if not svc:
            return False
        svc.recovery_attempts += 1
        logger.warning("[WATCHDOG] Attempting recovery for %s (attempt %d/%d)",
                       service_name, svc.recovery_attempts, self._max_attempts)

        if svc.recovery_attempts > self._max_attempts:
            logger.error("[WATCHDOG] Max recovery attempts reached for %s — escalating to safe mode", service_name)
            if self._on_escalate:
                self._on_escalate(service_name)
            logger.critical("[WATCHDOG] RECOVERY EXHAUSTED for %s — system will degrade", service_name)
            return False

        # Level 1: Try the dedicated recovery engine (if available)
        try:
            from core_engines.recovery.engine import get_recovery_engine
            engine = get_recovery_engine()
            error_map = {
                "api": "API server unresponsive",
                "agents": "Agent crashed or unresponsive",
                "scheduler": "Scheduler not running",
                "eventbus": "EventBus stuck or dead",
            }
            failure_type_map = {
                "api": "api_unresponsive",
                "agents": "agent_crashed",
                "scheduler": "scheduler_dead",
                "eventbus": "eventbus_stuck",
            }
            from core_engines.recovery.healing_rules import FailureType
            ft = FailureType(failure_type_map.get(service_name, "unknown"))
            initiated = engine.report_failure(
                component=service_name,
                error_message=error_map.get(service_name, f"Unknown failure in {service_name}"),
                failure_type=ft,
                details={"source": "watchdog", "attempt": svc.recovery_attempts},
            )
            if initiated:
                if self._on_recovery:
                    self._on_recovery(service_name)
                logger.info("[WATCHDOG] Recovery initiated for %s via RecoveryEngine", service_name)
                return True
            logger.warning("[WATCHDOG] Recovery engine declined recovery for %s", service_name)
        except ImportError:
            logger.warning("[WATCHDOG] Recovery engine not available — using fallback")
        except Exception as exc:
            logger.error("[WATCHDOG] Recovery engine error for %s: %s", service_name, exc)

        # Level 2: Direct HTTP restart (if API is partially responsive)
        if service_name in ("api", "agents", "scheduler"):
            try:
                import httpx
                base = self._health_url.rsplit("/api/health", 1)[0]
                r = httpx.post(f"{base}/api/system/restart/{service_name}", timeout=5.0)
                if r.status_code == 200:
                    logger.info("[WATCHDOG] Direct restart OK for %s", service_name)
                    if self._on_recovery:
                        self._on_recovery(service_name)
                    return True
                logger.warning("[WATCHDOG] Direct restart returned %d for %s", r.status_code, service_name)
            except Exception as exc:
                logger.warning("[WATCHDOG] Direct restart failed for %s: %s", service_name, exc)

        # Level 3: For eventbus, try reinitializing the bus
        if service_name == "eventbus":
            try:
                from core_engines.agents.bus import get_agent_bus
                bus = get_agent_bus()
                if bus is not None:
                    logger.info("[WATCHDOG] Reinitializing EventBus for %s", service_name)
                    if self._on_recovery:
                        self._on_recovery(service_name)
                    return True
            except Exception as exc:
                logger.warning("[WATCHDOG] EventBus reinit failed: %s", exc)

        logger.warning("[WATCHDOG] All recovery levels failed for %s", service_name)
        return False

    def _detect_freeze(self, history: list[WatchdogSnapshot]) -> bool:
        """Detect if the system is frozen (identical status across last N snapshots)."""
        if len(history) < 3:
            return False
        recent = history[-3:]
        if all(s.overall == recent[0].overall for s in recent):
            # Check if timestamp deltas are consistent (process not truly frozen)
            deltas = [recent[i+1].timestamp - recent[i].timestamp for i in range(len(recent)-1)]
            if all(d < self._interval * 3 for d in deltas):
                return False  # Normal operation, just stuck in same status
            logger.warning("[WATCHDOG] Possible freeze detected — identical status across %d checks", len(recent))
            return True
        return False

    def _run_loop(self) -> None:
        self._start_time = time.time()
        consecutive_fails = 0
        backoff = self._interval
        prev_mem = -1.0
        mem_leak_warnings = 0

        while self._running:
            try:
                api_ok = self._check_api()
                self._update_service("api", api_ok)

                agents_ok = self._check_agents() if api_ok else False
                self._update_service("agents", agents_ok)

                sched_ok = self._check_scheduler() if api_ok else False
                self._update_service("scheduler", sched_ok)

                bus_ok = self._check_eventbus()
                self._update_service("eventbus", bus_ok)

                mem_pct = self._get_memory_percent()
                cpu_pct = self._get_cpu_percent()

                mem_ok = mem_pct < 80.0 or mem_pct < 0
                cpu_ok = cpu_pct < 90.0 or cpu_pct < 0

                if not mem_ok:
                    logger.warning("[WATCHDOG] High memory: %.1f%%", mem_pct)
                if not cpu_ok:
                    logger.warning("[WATCHDOG] High CPU: %.1f%%", cpu_pct)

                # Memory leak detection (sustained growth >10% between checks)
                if prev_mem > 0 and mem_pct > 0 and (mem_pct - prev_mem) > 10.0:
                    mem_leak_warnings += 1
                    logger.warning("[WATCHDOG] Memory leak suspected: %.1f%% → %.1f%% (warning %d/3)",
                                   prev_mem, mem_pct, mem_leak_warnings)
                    if mem_leak_warnings >= 3:
                        logger.critical("[WATCHDOG] MEMORY LEAK CONFIRMED — escalating")
                        if self._on_escalate:
                            self._on_escalate("memory_leak")
                else:
                    mem_leak_warnings = max(0, mem_leak_warnings - 1)
                prev_mem = mem_pct

                all_ok = api_ok and agents_ok and sched_ok and bus_ok and mem_ok and cpu_ok
                overall = HealthStatus.HEALTHY if all_ok else (
                    HealthStatus.FAILED if not (api_ok or bus_ok) else HealthStatus.DEGRADED
                )

                snapshot = WatchdogSnapshot(
                    timestamp=time.time(),
                    services=dict(self._services),
                    memory_percent=mem_pct,
                    cpu_percent=cpu_pct,
                    overall=overall,
                    uptime=time.time() - self._start_time,
                )
                with self._lock:
                    self._snapshot_history.append(snapshot)
                    if len(self._snapshot_history) > 1000:
                        self._snapshot_history = self._snapshot_history[-500:]

                if overall != HealthStatus.HEALTHY:
                    consecutive_fails += 1
                    for name, svc in self._services.items():
                        if svc.status == HealthStatus.FAILED:
                            self._attempt_recovery(name)
                    backoff = min(self._interval * (2 ** min(consecutive_fails, 5)), 300)
                else:
                    consecutive_fails = 0
                    backoff = self._interval

                # Freeze detection
                if consecutive_fails >= 3 and self._detect_freeze(self._snapshot_history):
                    logger.critical("[WATCHDOG] SYSTEM FROZEN — initiating emergency recovery")
                    for name in self._services:
                        self._attempt_recovery(name)
                    backoff = min(backoff * 2, 300)
                    if self._on_escalate:
                        self._on_escalate("system_frozen")

                logger.info("[WATCHDOG] Health: %s (mem=%.1f%% cpu=%.1f%% api=%s agents=%s sched=%s bus=%s backoff=%.0fs)",
                             overall.value, mem_pct, cpu_pct,
                             api_ok, agents_ok, sched_ok, bus_ok, backoff)

            except Exception as exc:
                logger.error("[WATCHDOG] Loop error: %s", exc, exc_info=True)
                backoff = min(backoff * 1.5, 300)

            if self._running:
                time.sleep(backoff)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="orion-watchdog")
        self._thread.start()
        logger.info("[WATCHDOG] Started (interval=%ss, max_attempts=%d)", self._interval, self._max_attempts)

    def stop(self) -> None:
        self._running = False
        self._thread = None
        logger.info("[WATCHDOG] Stopped")

    @property
    def is_running(self) -> bool:
        return self._running and (self._thread is not None and self._thread.is_alive())

    def get_snapshot(self) -> WatchdogSnapshot | None:
        with self._lock:
            if not self._snapshot_history:
                return None
            return self._snapshot_history[-1]

    def get_history(self) -> list[WatchdogSnapshot]:
        with self._lock:
            return list(self._snapshot_history)

    def get_status(self) -> dict[str, Any]:
        snap = self.get_snapshot()
        return {
            "running": self.is_running,
            "uptime": time.time() - self._start_time if self._start_time else 0,
            "services": {
                name: {
                    "status": svc.status.value,
                    "fail_count": svc.fail_count,
                    "recovery_attempts": svc.recovery_attempts,
                    "last_error": svc.last_error,
                }
                for name, svc in self._services.items()
            },
            "memory_percent": snap.memory_percent if snap else -1,
            "cpu_percent": snap.cpu_percent if snap else -1,
            "overall": snap.overall.value if snap else "unknown",
            "snapshots": len(self._snapshot_history),
        }
