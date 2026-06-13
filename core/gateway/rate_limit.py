"""Simple in-memory rate limiter for API endpoints.

Uses token bucket algorithm. No external dependencies.
Single-instance only; swap for Redis in multi-instance deployments.
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple


class TokenBucket:
    """Per-key token bucket rate limiter."""

    def __init__(self, rate: float = 10.0, burst: int = 20) -> None:
        self.rate = rate
        self.burst = burst
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def _refill(self, key: str) -> Tuple[float, float]:
        now = time.monotonic()
        tokens, last = self._buckets.get(key, (float(self.burst), now))
        elapsed = now - last
        tokens = min(float(self.burst), tokens + elapsed * self.rate)
        return tokens, now

    def consume(self, key: str, cost: float = 1.0) -> bool:
        tokens, now = self._refill(key)
        if tokens >= cost:
            self._buckets[key] = (tokens - cost, now)
            return True
        self._buckets[key] = (tokens, now)
        return False

    def remaining(self, key: str) -> float:
        tokens, _ = self._refill(key)
        return tokens

    def reset(self, key: str) -> None:
        self._buckets.pop(key, None)


_rate_limiter: Optional[TokenBucket] = None


def get_rate_limiter() -> TokenBucket:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TokenBucket(rate=10.0, burst=20)
    return _rate_limiter
