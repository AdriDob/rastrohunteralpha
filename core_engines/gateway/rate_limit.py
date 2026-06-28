"""Simple in-memory rate limiter for API endpoints.

Uses token bucket algorithm. No external dependencies.
Single-instance only; swap for Redis in multi-instance deployments.
"""

from __future__ import annotations

import re
import time


class RateLimitRule:
    """A rate limit rule with path pattern matching."""

    def __init__(self, pattern: str, rate: float, burst: int) -> None:
        self.pattern = re.compile(pattern)
        self.rate = rate
        self.burst = burst


class TokenBucket:
    """Per-key token bucket rate limiter."""

    def __init__(self, rate: float = 30.0, burst: int = 50) -> None:
        self.default_rate = rate
        self.default_burst = burst
        self._buckets: dict[str, tuple[float, float]] = {}
        self._rules: list[RateLimitRule] = []

    def add_rule(self, pattern: str, rate: float, burst: int) -> None:
        self._rules.append(RateLimitRule(pattern, rate, burst))

    def _get_limits(self, key: str) -> tuple[float, int]:
        for rule in self._rules:
            if rule.pattern.search(key):
                return rule.rate, rule.burst
        return self.default_rate, self.default_burst

    def _refill(self, key: str, burst: int) -> tuple[float, float]:
        now = time.monotonic()
        tokens, last = self._buckets.get(key, (float(burst), now))
        rate, _ = self._get_limits(key)
        elapsed = now - last
        tokens = min(float(burst), tokens + elapsed * rate)
        return tokens, now

    def consume(self, key: str, cost: float = 1.0) -> bool:
        _, burst = self._get_limits(key)
        tokens, now = self._refill(key, burst)
        if tokens >= cost:
            self._buckets[key] = (tokens - cost, now)
            return True
        self._buckets[key] = (tokens, now)
        return False

    def remaining(self, key: str) -> float:
        _, burst = self._get_limits(key)
        tokens, _ = self._refill(key, burst)
        return tokens

    def reset(self, key: str) -> None:
        self._buckets.pop(key, None)


_rate_limiter: TokenBucket | None = None


def reset_rate_limiter() -> None:
    """Reset the rate limiter singleton (useful for tests)."""
    global _rate_limiter
    _rate_limiter = None


def get_rate_limiter() -> TokenBucket:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TokenBucket(rate=30.0, burst=50)
        _rate_limiter.add_rule(r"/api/auth/login", rate=5.0, burst=10)
        _rate_limiter.add_rule(r"/api/auth/refresh", rate=3.0, burst=5)
        _rate_limiter.add_rule(r"/api/overview", rate=10.0, burst=20)
        _rate_limiter.add_rule(r"/api/digest", rate=10.0, burst=20)
    return _rate_limiter
