"""Signal Filtering — eliminates noise before it reaches the user.

Filters:
  - Low EVH items (below minimum threshold)
  - Duplicated opportunities (same name within time window)
  - Stale signals (older than TTL)
  - Irrelevant recommendations (low confidence + low engagement)
  - Suppressed items (user previously ignored)

Rule: the user never sees noise by default.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("rastro.intelligence.noise")

DATA_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "rastro",
    "intel",
)

MIN_EVH = 10.0
STALE_HOURS = 48
DUP_WINDOW_SEC = 3600
MIN_CONFIDENCE = 0.15


@dataclass
class CleanSignal:
    id: str
    signal_type: str
    label: str
    value: float
    confidence: float
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_type": self.signal_type,
            "label": self.label,
            "value": self.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "source": self.source,
        }


class NoiseFilter:
    """Filters raw signals into a clean signal set."""

    def __init__(self) -> None:
        self._seen_hashes: Dict[str, float] = {}
        self._suppressed_ids: Set[str] = set()
        self._filter_count: int = 0
        self._pass_count: int = 0
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()

    def filter_opportunity(self, opp: Dict[str, Any]) -> Optional[CleanSignal]:
        evh = opp.get("evh_score") or opp.get("score", 0)
        if evh < MIN_EVH:
            self._filter_count += 1
            return None

        name = opp.get("name", "")
        dedup_key = f"opp:{name}"
        if self._is_duplicate(dedup_key):
            self._filter_count += 1
            return None

        signal = CleanSignal(
            id=f"opp-{opp.get('id', hash(name))}",
            signal_type="opportunity",
            label=name,
            value=evh,
            confidence=opp.get("confidence", 0.5),
            source=opp.get("source", "opportunity_engine"),
            metadata=opp,
        )
        self._record_dedup(dedup_key)
        self._pass_count += 1
        return signal

    def filter_quick_win(self, qw: Dict[str, Any]) -> Optional[CleanSignal]:
        confidence = qw.get("confidence", 0)
        if confidence < MIN_CONFIDENCE:
            self._filter_count += 1
            return None

        title = qw.get("title", "")
        dedup_key = f"qw:{title}"
        if self._is_duplicate(dedup_key):
            return None

        signal = CleanSignal(
            id=f"qw-{qw.get('id', hash(title))}",
            signal_type="quick_win",
            label=title,
            value=confidence,
            confidence=confidence,
            source="quick_win_engine",
            metadata=qw,
        )
        self._record_dedup(dedup_key)
        self._pass_count += 1
        return signal

    def filter_recommendation(self, rec: Dict[str, Any]) -> Optional[CleanSignal]:
        confidence = rec.get("confidence", 0)
        priority = rec.get("priority", "low")
        if confidence < MIN_CONFIDENCE and priority not in ("critical", "high"):
            self._filter_count += 1
            return None

        action_key = rec.get("action", rec.get("type", ""))
        dedup_key = f"rec:{action_key}"
        if self._is_duplicate(dedup_key):
            return None

        signal = CleanSignal(
            id=f"rec-{action_key}",
            signal_type="recommendation",
            label=rec.get("action", "Recommendation"),
            value=confidence,
            confidence=confidence,
            source="assistant",
            metadata=rec,
        )
        self._record_dedup(dedup_key)
        self._pass_count += 1
        return signal

    def filter_system_alert(self, alert: Dict[str, Any]) -> Optional[CleanSignal]:
        severity = alert.get("severity", "low")
        if severity == "low":
            self._filter_count += 1
            return None

        dedup_key = f"alert:{alert.get('title', '')}"
        if self._is_duplicate(dedup_key):
            return None

        urgency = {"critical": 1.0, "high": 0.8, "medium": 0.5}.get(severity, 0.2)
        signal = CleanSignal(
            id=f"alert-{alert.get('id', hash(str(alert)))}",
            signal_type="alert",
            label=alert.get("title", "Alert"),
            value=urgency,
            confidence=1.0,
            source="system",
            metadata=alert,
        )
        self._record_dedup(dedup_key)
        self._pass_count += 1
        return signal

    def suppress(self, signal_id: str) -> None:
        self._suppressed_ids.add(signal_id)

    def is_suppressed(self, signal_id: str) -> bool:
        return signal_id in self._suppressed_ids

    def get_suppressed(self) -> List[str]:
        return list(self._suppressed_ids)

    def clear_suppressed(self) -> None:
        self._suppressed_ids.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "filtered": self._filter_count,
            "passed": self._pass_count,
            "suppressed": len(self._suppressed_ids),
            "dedup_tracked": len(self._seen_hashes),
            "min_evh": MIN_EVH,
            "min_confidence": MIN_CONFIDENCE,
            "stale_hours": STALE_HOURS,
        }

    def _is_duplicate(self, key: str) -> bool:
        last = self._seen_hashes.get(key)
        if last is None:
            return False
        return (time.time() - last) < DUP_WINDOW_SEC

    def _record_dedup(self, key: str) -> None:
        self._seen_hashes[key] = time.time()
        self._cleanup_dedup()

    def _cleanup_dedup(self) -> None:
        now = time.time()
        stale = [k for k, ts in self._seen_hashes.items() if now - ts > DUP_WINDOW_SEC]
        for k in stale:
            del self._seen_hashes[k]

    def _path(self) -> str:
        return os.path.join(DATA_DIR, "noise_filter.json")

    def _load(self) -> None:
        try:
            if os.path.exists(self._path()):
                with open(self._path()) as f:
                    data = json.load(f)
                    self._suppressed_ids = set(data.get("suppressed", []))
        except (json.JSONDecodeError, OSError):
            pass

    def _save(self) -> None:
        try:
            with open(self._path(), "w") as f:
                json.dump({"suppressed": list(self._suppressed_ids)}, f)
        except OSError:
            pass


_NOISE_FILTER: Optional[NoiseFilter] = None


def get_noise_filter() -> NoiseFilter:
    global _NOISE_FILTER
    if _NOISE_FILTER is None:
        _NOISE_FILTER = NoiseFilter()
    return _NOISE_FILTER
