"""Circuit breaker — prevents infinite recovery loops with cooldown and max attempts."""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any

logger = logging.getLogger("rastro.recovery.circuit_breaker")

MAX_FAILURES = 3
COOLDOWN_SECONDS = 60.0
HALF_OPEN_RETRIES = 1


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-component circuit breaker.

    States:
      CLOSED   — normal operation, failures are counted
      OPEN     — too many failures, recovery paused
      HALF_OPEN — after cooldown, one attempt allowed
    """

    def __init__(
        self,
        component: str,
        max_failures: int = MAX_FAILURES,
        cooldown: float = COOLDOWN_SECONDS,
    ) -> None:
        self.component = component
        self.max_failures = max_failures
        self.cooldown = cooldown
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._last_failure_time: float = 0.0
        self._half_open_attempts = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._opened_at and (time.monotonic() - self._opened_at) >= self.cooldown:
                self._state = CircuitState.HALF_OPEN
                self._half_open_attempts = 0
                logger.info("[CB] %s circuit → half_open (cooldown elapsed)", self.component)
        return self._state

    def record_failure(self) -> bool:
        """Record a failure. Returns True if circuit is now open."""
        now = time.monotonic()
        self._last_failure_time = now
        self._failure_count += 1

        current = self.state
        if current == CircuitState.HALF_OPEN:
            self._half_open_attempts += 1
            if self._half_open_attempts >= HALF_OPEN_RETRIES:
                self._open()
                return True
            return False

        if self._failure_count >= self.max_failures:
            self._open()
            return True

        return False

    def record_success(self) -> None:
        """Record a successful recovery — reset the breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        self._half_open_attempts = 0
        logger.info("[CB] %s circuit → closed (success)", self.component)

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        logger.error(
            "[CB] %s circuit → OPEN (%d failures, cooldown=%.0fs)",
            self.component, self._failure_count, self.cooldown,
        )

    def can_attempt(self) -> bool:
        return self.state != CircuitState.OPEN

    def can_attempt_recovery(self) -> bool:
        current = self.state
        if current == CircuitState.OPEN:
            return False
        if current == CircuitState.HALF_OPEN:
            return self._half_open_attempts < HALF_OPEN_RETRIES
        return self._failure_count < self.max_failures

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        self._half_open_attempts = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "max_failures": self.max_failures,
            "cooldown": self.cooldown,
            "opened": self._opened_at is not None,
        }


class CircuitBreakerRegistry:
    """Manages circuit breakers for all components."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, component: str) -> CircuitBreaker:
        if component not in self._breakers:
            self._breakers[component] = CircuitBreaker(component)
        return self._breakers[component]

    def all_snapshots(self) -> dict[str, dict[str, Any]]:
        return {name: cb.snapshot() for name, cb in self._breakers.items()}

    def reset_all(self) -> None:
        for cb in self._breakers.values():
            cb.reset()
