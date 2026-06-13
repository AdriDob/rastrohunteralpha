"""Snapshot history manager for opportunity intelligence.

Stores point-in-time snapshots in memory with periodic persistence.
Read-only history — never modifies pipeline data.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core_engines.opportunity.models import Opportunity, OpportunitySnapshot

logger = logging.getLogger("rastro.opportunity.history")

_GLOBAL_HISTORY: Optional["HistoryManager"] = None

# In-memory snapshot store. In production this could be backed by the DB.
_snapshots: List[OpportunitySnapshot] = []


class HistoryManager:
    """Manages opportunity snapshots for trend analysis."""

    def __init__(self) -> None:
        self._snapshots: List[OpportunitySnapshot] = _snapshots

    def store_snapshot(
        self,
        opportunities: List[Opportunity],
        period: str = "daily",
        metrics: Optional[Dict[str, Any]] = None,
    ) -> OpportunitySnapshot:
        """Create and store a point-in-time snapshot.

        Period: daily, weekly, or monthly.
        """
        now = datetime.now(timezone.utc).isoformat()
        snapshot = OpportunitySnapshot(
            id=str(uuid.uuid4())[:12],
            timestamp=now,
            period=period,
            opportunities=opportunities,
            metrics=metrics or {},
        )
        self._snapshots.append(snapshot)

        # Keep max 365 days of daily, 52 weeks, 24 months
        self._trim()
        logger.info("Stored %s snapshot with %d opportunities", period, len(opportunities))
        return snapshot

    def get_snapshots(
        self,
        period: Optional[str] = None,
        limit: int = 30,
    ) -> List[OpportunitySnapshot]:
        """Return snapshots, newest first."""
        result = list(self._snapshots)
        if period:
            result = [s for s in result if s.period == period]
        result.sort(key=lambda s: s.timestamp, reverse=True)
        return result[:limit]

    def get_latest(self) -> Optional[OpportunitySnapshot]:
        if not self._snapshots:
            return None
        return max(self._snapshots, key=lambda s: s.timestamp)

    def get_trends(self) -> Dict[str, Any]:
        """Compute trend data from historical snapshots."""
        if len(self._snapshots) < 2:
            return {"status": "insufficient_data"}

        sorted_snaps = sorted(self._snapshots, key=lambda s: s.timestamp)
        latest = sorted_snaps[-1]
        oldest = sorted_snaps[0]

        def avg_score(snap: OpportunitySnapshot) -> float:
            scores = [o.score.overall for o in snap.opportunities if o.score]
            return sum(scores) / max(len(scores), 1) if scores else 0.0

        return {
            "snapshots_count": len(sorted_snaps),
            "latest_snapshot": latest.timestamp,
            "oldest_snapshot": oldest.timestamp,
            "average_score_current": round(avg_score(latest), 4),
            "average_score_oldest": round(avg_score(oldest), 4),
            "score_trend": round(avg_score(latest) - avg_score(oldest), 4),
            "opportunity_count_current": len(latest.opportunities),
            "opportunity_count_oldest": len(oldest.opportunities),
            "count_trend": len(latest.opportunities) - len(oldest.opportunities),
        }

    def clear(self) -> None:
        self._snapshots.clear()

    def _trim(self) -> None:
        """Keep max entries per period type."""
        limits = {"daily": 365, "weekly": 52, "monthly": 24}
        for period, max_count in limits.items():
            entries = [s for s in self._snapshots if s.period == period]
            if len(entries) > max_count:
                entries.sort(key=lambda s: s.timestamp)
                to_remove = set(id(e) for e in entries[:-max_count])
                self._snapshots = [s for s in self._snapshots if id(s) not in to_remove]


def get_history_manager() -> HistoryManager:
    global _GLOBAL_HISTORY
    if _GLOBAL_HISTORY is None:
        _GLOBAL_HISTORY = HistoryManager()
    return _GLOBAL_HISTORY
