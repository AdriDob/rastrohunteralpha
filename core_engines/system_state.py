"""Global system state manager.

Tracks the health and readiness of all system services.
Publishes state changes to the event bus for reactive UI updates.

States:
  - BOOTING: system is starting up
  - READY: all core services healthy
  - DEGRADED: some services unhealthy, system still usable
  - FAILED: critical services down, system non-functional
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core_engines.events.event_bus import get_event_bus

logger = logging.getLogger("rastro.system_state")

SYSTEM_STATE_BOOTING = "BOOTING"
SYSTEM_STATE_READY = "READY"
SYSTEM_STATE_DEGRADED = "DEGRADED"
SYSTEM_STATE_FAILED = "FAILED"

ALL_STATES = [SYSTEM_STATE_BOOTING, SYSTEM_STATE_READY, SYSTEM_STATE_DEGRADED, SYSTEM_STATE_FAILED]

StateChangeHandler = Callable[[str, str], None]  # (service_name, new_state)


@dataclass
class ServiceHealth:
    """Health record for a single service."""
    name: str
    state: str = "unknown"
    last_healthy: float | None = None
    last_seen: float | None = None
    error_count: int = 0
    last_error: str | None = None


class SystemState:
    """Global system state — single source of truth for service health."""

    def __init__(self) -> None:
        self._system_state: str = SYSTEM_STATE_BOOTING
        self._services: dict[str, ServiceHealth] = {}
        self._state_change_handlers: list[StateChangeHandler] = []
        self._on_state_change_callbacks: list[Callable[[str], None]] = []
        self._boot_start: float = time.time()
        self._last_state_change: float = time.time()

    def register_service(self, name: str) -> None:
        """Register a service for health tracking."""
        if name not in self._services:
            self._services[name] = ServiceHealth(name=name)

    def report_healthy(self, name: str) -> None:
        """Mark a service as healthy."""
        svc = self._services.get(name)
        if svc is None:
            self.register_service(name)
            svc = self._services[name]
        svc.state = "healthy"
        svc.last_healthy = time.time()
        svc.last_seen = time.time()
        self._recompute()

    def report_unhealthy(self, name: str, error: str | None = None) -> None:
        """Mark a service as unhealthy."""
        svc = self._services.get(name)
        if svc is None:
            self.register_service(name)
            svc = self._services[name]
        svc.state = "unhealthy"
        svc.last_seen = time.time()
        svc.error_count += 1
        svc.last_error = error
        self._recompute()

    def report_error(self, name: str, error: str) -> None:
        """Report an error for a service."""
        self.report_unhealthy(name, error=error)

    def get_service(self, name: str) -> ServiceHealth | None:
        return self._services.get(name)

    def get_state(self) -> str:
        return self._system_state

    def get_services(self) -> list[dict[str, Any]]:
        return [
            {
                "name": svc.name,
                "state": svc.state,
                "last_healthy": svc.last_healthy,
                "last_seen": svc.last_seen,
                "error_count": svc.error_count,
                "last_error": svc.last_error,
            }
            for svc in self._services.values()
        ]

    def is_ready(self) -> bool:
        return self._system_state == SYSTEM_STATE_READY

    def subscribe(self, handler: StateChangeHandler) -> None:
        """Subscribe to state changes."""
        self._state_change_handlers.append(handler)

    def on_state_change(self, callback: Callable[[str], None]) -> None:
        self._on_state_change_callbacks.append(callback)

    def get_uptime(self) -> float:
        return time.time() - self._boot_start

    def get_summary(self) -> dict[str, Any]:
        services = self.get_services()
        healthy = sum(1 for s in services if s["state"] == "healthy")
        unhealthy = sum(1 for s in services if s["state"] == "unhealthy")
        return {
            "system_state": self._system_state,
            "uptime_seconds": self.get_uptime(),
            "services_total": len(services),
            "services_healthy": healthy,
            "services_unhealthy": unhealthy,
            "boot_start": self._boot_start,
        }

    def _recompute(self) -> None:
        """Recompute the aggregate system state from all services."""
        services = self.get_services()
        if not services:
            return

        all_healthy = all(s["state"] == "healthy" for s in services)
        any_unhealthy = any(s["state"] == "unhealthy" for s in services)
        all(s["state"] == "unknown" for s in services)

        new_state = self._system_state
        if self._system_state == SYSTEM_STATE_BOOTING and all_healthy:
            new_state = SYSTEM_STATE_READY
        elif self._system_state == SYSTEM_STATE_BOOTING and any_unhealthy or self._system_state == SYSTEM_STATE_READY and any_unhealthy:
            new_state = SYSTEM_STATE_DEGRADED
        elif self._system_state == SYSTEM_STATE_DEGRADED and all_healthy:
            new_state = SYSTEM_STATE_READY

        if new_state != self._system_state:
            old = self._system_state
            self._system_state = new_state
            self._last_state_change = time.time()
            for handler in self._state_change_handlers:
                try:
                    handler(old, new_state)
                except Exception as exc:
                    logger.warning("State change handler error: %s", exc)
            for cb in self._on_state_change_callbacks:
                try:
                    cb(new_state)
                except Exception as exc:
                    logger.warning("State change callback error: %s", exc)
            try:
                get_event_bus().publish(f"system:state:{new_state.lower()}", previous=old, current=new_state)
            except Exception as exc:
                logger.warning("State change event bus error: %s", exc)


_STATE: SystemState | None = None


def get_system_state() -> SystemState:
    global _STATE
    if _STATE is None:
        _STATE = SystemState()
    return _STATE
