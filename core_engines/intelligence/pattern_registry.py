import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

LOG = logging.getLogger("rastro.intelligence.patterns")


@dataclass(frozen=True)
class PatternKey:
    dimension: str
    value: str


@dataclass
class PatternStats:
    count: int = 0
    confirmed_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    total_payout: float = 0.0
    min_payout: float = 0.0
    max_payout: float = 0.0
    total_validation_hours: float = 0.0
    total_report_hours: float = 0.0
    total_confidence: float = 0.0
    last_seen: str | None = None
    first_seen: str | None = None

    @property
    def avg_payout(self) -> float:
        return round(self.total_payout / self.count, 2) if self.count else 0.0

    @property
    def avg_validation_hours(self) -> float:
        return round(self.total_validation_hours / self.count, 2) if self.count else 0.0

    @property
    def avg_report_hours(self) -> float:
        return round(self.total_report_hours / self.count, 2) if self.count else 0.0

    @property
    def avg_confidence(self) -> float:
        return round(self.total_confidence / self.count, 2) if self.count else 0.0

    @property
    def acceptance_rate(self) -> float:
        total = self.confirmed_count + self.rejected_count
        return round(self.confirmed_count / total, 4) if total else 0.0

    @property
    def duplicate_rate(self) -> float:
        return round(self.duplicate_count / self.count, 4) if self.count else 0.0


class PatternRegistry:
    def __init__(self) -> None:
        self._patterns: dict[str, dict[str, PatternStats]] = defaultdict(lambda: defaultdict(PatternStats))
        self._lock = Lock()

    def record(
        self,
        dimension: str,
        value: str,
        confirmed: bool = False,
        rejected: bool = False,
        duplicate: bool = False,
        payout: float = 0.0,
        validation_hours: float = 0.0,
        report_hours: float = 0.0,
        confidence: float = 0.0,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            stats = self._patterns[dimension][value]
            stats.count += 1
            if confirmed:
                stats.confirmed_count += 1
            if rejected:
                stats.rejected_count += 1
            if duplicate:
                stats.duplicate_count += 1
            stats.total_payout += payout
            stats.total_validation_hours += validation_hours
            stats.total_report_hours += report_hours
            stats.total_confidence += confidence
            stats.last_seen = now
            if stats.first_seen is None:
                stats.first_seen = now
            if payout > 0:
                if stats.min_payout == 0 or payout < stats.min_payout:
                    stats.min_payout = payout
                if payout > stats.max_payout:
                    stats.max_payout = payout

    def get_stats(self, dimension: str | None = None, value: str | None = None) -> dict[str, Any]:
        with self._lock:
            if dimension and value:
                s = self._patterns.get(dimension, {}).get(value)
                if s is None:
                    return {}
                return asdict(s)
            if dimension:
                return {v: asdict(s) for v, s in self._patterns.get(dimension, {}).items()}
            return {
                dim: {v: asdict(s) for v, s in vals.items()}
                for dim, vals in self._patterns.items()
            }

    def get_top(self, dimension: str, metric: str = "count", limit: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            items = []
            for value, stats in self._patterns.get(dimension, {}).items():
                d = asdict(stats)
                d["dimension"] = dimension
                d["value"] = value
                items.append(d)
            items.sort(key=lambda x: x.get(metric, 0), reverse=True)
            return items[:limit]

    def get_dimensions(self) -> list[str]:
        with self._lock:
            return list(self._patterns.keys())

    def get_values(self, dimension: str) -> list[str]:
        with self._lock:
            return list(self._patterns.get(dimension, {}).keys())

    def clear(self) -> None:
        with self._lock:
            self._patterns.clear()

    def to_dict(self) -> dict[str, Any]:
        return self.get_stats()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatternRegistry":
        reg = cls()
        for dimension, values in data.items():
            for value, stats_dict in values.items():
                stats = PatternStats(**stats_dict)
                reg._patterns[dimension][value] = stats
        return reg


_registry: PatternRegistry | None = None
_registry_lock = Lock()


def get_registry() -> PatternRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = PatternRegistry()
    return _registry


def reset_registry() -> None:
    global _registry
    with _registry_lock:
        _registry = None
