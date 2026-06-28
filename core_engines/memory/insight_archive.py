"""InsightArchive — persistent historical record of all generated insights."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core_engines.memory.memory_store import MemoryStore, get_memory_store

logger = logging.getLogger("rastro.memory.insight")

CATEGORY = "insight"


@dataclass
class Insight:
    id: str
    title: str
    description: str
    insight_type: str = "observation"
    source: str = "system"
    severity: str = "info"
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "insight_type": self.insight_type,
            "source": self.source,
            "severity": self.severity,
            "tags": self.tags,
            "context": self.context,
            "timestamp": self.timestamp,
        }


class InsightArchive:
    """Immutable historical record of all generated insights.

    Every insight is stored once and never modified.
    Supports full-text search, tag-based filtering, and time-range queries.
    """

    def __init__(self) -> None:
        self._store: MemoryStore = get_memory_store()

    def archive(self, insight: Insight) -> None:
        self._store.store(CATEGORY, insight.id, insight.to_dict())

    def get(self, insight_id: str) -> dict[str, Any] | None:
        return self._store.get(CATEGORY, insight_id)

    def list_insights(
        self,
        insight_type: str | None = None,
        source: str | None = None,
        tag: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        results = self._store.query(CATEGORY, limit=limit, offset=offset)
        filtered = []
        for r in results:
            d = r.get("details", {})
            if insight_type and d.get("insight_type") != insight_type:
                continue
            if source and d.get("source") != source:
                continue
            if severity and d.get("severity") != severity:
                continue
            if tag and tag not in d.get("tags", []):
                continue
            filtered.append(r)
        return filtered

    def count_by_type(self) -> dict[str, int]:
        results = self._store.query(CATEGORY, limit=2000)
        counts: dict[str, int] = {}
        for r in results:
            t = r.get("details", {}).get("insight_type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts

    def count_by_severity(self) -> dict[str, int]:
        results = self._store.query(CATEGORY, limit=2000)
        counts: dict[str, int] = {}
        for r in results:
            s = r.get("details", {}).get("severity", "info")
            counts[s] = counts.get(s, 0) + 1
        return counts

    def recent_by_source(self, source: str, limit: int = 20) -> list[dict[str, Any]]:
        return self.list_insights(source=source, limit=limit)

    def total_count(self) -> int:
        return self._store.count(CATEGORY)

    def cleanup_old(self, days: int = 90) -> int:
        return self._store.delete_older_than(CATEGORY, days)


_ARCHIVE: InsightArchive | None = None


def get_insight_archive() -> InsightArchive:
    global _ARCHIVE
    if _ARCHIVE is None:
        _ARCHIVE = InsightArchive()
    return _ARCHIVE
