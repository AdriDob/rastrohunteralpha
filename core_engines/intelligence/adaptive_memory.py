import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from database.db import SessionLocal

LOG = logging.getLogger("rastro.intelligence.memory")

from core.intelligence.pattern_registry import PatternRegistry, get_registry
from core.intelligence.historical_analyzer import (
    HistoricalSummary, analyze_historical_data,
)
from core.intelligence.trend_detector import TrendReport, detect_trends
from core.intelligence.recommendation_engine import (
    RecommendationBundle, generate_recommendations,
)
from core.intelligence.learning_snapshot import (
    LearningSnapshot, generate_snapshot,
)


@dataclass
class AdaptiveMemoryState:
    last_analysis: Optional[str] = None
    last_snapshot_daily: Optional[str] = None
    last_snapshot_weekly: Optional[str] = None
    last_snapshot_monthly: Optional[str] = None
    total_patterns_learned: int = 0
    total_recommendations_generated: int = 0
    total_snapshots_created: int = 0
    total_analysis_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AdaptiveMemory:
    def __init__(self, registry: Optional[PatternRegistry] = None) -> None:
        self._registry = registry or get_registry()
        self._state = AdaptiveMemoryState()
        self._lock = Lock()
        self._history_cache: Optional[HistoricalSummary] = None

    @property
    def registry(self) -> PatternRegistry:
        return self._registry

    @property
    def state(self) -> AdaptiveMemoryState:
        return self._state

    def analyze(self) -> HistoricalSummary:
        import time
        t0 = time.monotonic()
        history = analyze_historical_data(registry=self._registry)
        elapsed = time.monotonic() - t0

        with self._lock:
            self._state.last_analysis = datetime.now(timezone.utc).isoformat()
            self._state.total_analysis_time_ms += round(elapsed * 1000, 1)
            self._history_cache = history
        return history

    def detect_trends(self) -> TrendReport:
        return detect_trends(
            registry=self._registry,
            history=self._history_cache,
        )

    def recommend(self) -> RecommendationBundle:
        trends = self.detect_trends()
        recs = generate_recommendations(
            history=self._history_cache,
            trends=trends,
            registry=self._registry,
        )
        with self._lock:
            rec_count = (
                len(recs.targets)
                + len(recs.surfaces)
                + len(recs.quick_wins)
                + len(recs.reports)
            )
            self._state.total_recommendations_generated += rec_count
        return recs

    def snapshot(self, snapshot_type: str = "daily") -> LearningSnapshot:
        snap = generate_snapshot(snapshot_type)
        with self._lock:
            self._state.total_snapshots_created += 1
            if snapshot_type == "daily":
                self._state.last_snapshot_daily = snap.generated_at
            elif snapshot_type == "weekly":
                self._state.last_snapshot_weekly = snap.generated_at
            elif snapshot_type == "monthly":
                self._state.last_snapshot_monthly = snap.generated_at
        self._persist_snapshot(snap)
        return snap

    def get_history(self) -> Optional[HistoricalSummary]:
        if self._history_cache is None:
            return self.analyze()
        return self._history_cache

    def get_snapshots(
        self, limit: int = 10, offset: int = 0
    ) -> List[Dict[str, Any]]:
        session = SessionLocal()
        try:
            from database.models import MemoryRecord
            records = (
                session.query(MemoryRecord)
                .filter(MemoryRecord.category == "learning_snapshot")
                .order_by(MemoryRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            results = []
            for r in records:
                details = {}
                if r.details:
                    try:
                        details = json.loads(r.details)
                    except (json.JSONDecodeError, ValueError):
                        details = {"raw": r.details}
                results.append({
                    "id": r.id,
                    "key": r.key,
                    "details": details,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })
            return results
        finally:
            session.close()

    def _persist_snapshot(self, snap: LearningSnapshot) -> None:
        session = SessionLocal()
        try:
            from database.models import MemoryRecord
            record = MemoryRecord(
                category="learning_snapshot",
                key=f"{snap.snapshot_type}:{snap.period_end[:10]}",
                details=json.dumps(snap.to_dict()),
            )
            session.add(record)
            session.commit()
        except Exception as e:
            LOG.warning("Failed to persist snapshot: %s", e)
            session.rollback()
        finally:
            session.close()

    def get_state(self) -> Dict[str, Any]:
        return self._state.to_dict()

    def clear(self) -> None:
        self._registry.clear()
        self._state = AdaptiveMemoryState()
        self._history_cache = None


_memory: Optional[AdaptiveMemory] = None
_memory_lock = Lock()


def get_memory() -> AdaptiveMemory:
    global _memory
    if _memory is None:
        with _memory_lock:
            if _memory is None:
                _memory = AdaptiveMemory()
    return _memory


def reset_memory() -> None:
    global _memory
    with _memory_lock:
        _memory = None
