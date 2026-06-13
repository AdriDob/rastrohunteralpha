"""
intelligence.observability — Metrics and observability for the intelligence layer.

Tracks:
- Active bundles count
- Last update time per artifact
- Recompute times
- Cache hits/misses
- Dependency updates
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("rastro.intelligence.observability")


@dataclass
class ArtifactMetrics:
    artifact_type: str = ""
    version: int = 0
    last_updated: str = ""
    recompute_count: int = 0
    recompute_time_ms: float = 0.0
    total_recompute_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def avg_recompute_time_ms(self) -> float:
        if self.recompute_count:
            return round(self.total_recompute_time_ms / self.recompute_count, 2)
        return 0.0


@dataclass
class SystemMetrics:
    active_artifacts: int = 0
    total_recomputes: int = 0
    total_cache_hits: int = 0
    total_cache_misses: int = 0
    total_cache_invalidations: int = 0
    anti_drift_violations: int = 0
    events_emitted: int = 0
    artifacts: Dict[str, ArtifactMetrics] = field(default_factory=dict)
    last_pipeline_run: str = ""
    system_uptime: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_artifacts": self.active_artifacts,
            "total_recomputes": self.total_recomputes,
            "total_cache_hits": self.total_cache_hits,
            "total_cache_misses": self.total_cache_misses,
            "total_cache_invalidations": self.total_cache_invalidations,
            "anti_drift_violations": self.anti_drift_violations,
            "events_emitted": self.events_emitted,
            "last_pipeline_run": self.last_pipeline_run,
            "system_uptime": self.system_uptime,
            "artifacts": {
                k: {
                    "version": v.version,
                    "last_updated": v.last_updated,
                    "recompute_count": v.recompute_count,
                    "avg_recompute_time_ms": v.avg_recompute_time_ms,
                    "cache_hits": v.cache_hits,
                    "cache_misses": v.cache_misses,
                }
                for k, v in self.artifacts.items()
            },
        }


class ObservabilityCollector:
    """
    Collects observability metrics for the intelligence layer.
    """

    def __init__(self) -> None:
        self._start_time = time.time()
        self._metrics: Dict[str, ArtifactMetrics] = {}
        self._current_recompute: Dict[str, float] = {}

    def start_recompute(self, artifact_type: str) -> None:
        if artifact_type not in self._metrics:
            self._metrics[artifact_type] = ArtifactMetrics(artifact_type=artifact_type)
        self._current_recompute[artifact_type] = time.time()

    def finish_recompute(self, artifact_type: str, version: int) -> None:
        elapsed_ms = 0.0
        start = self._current_recompute.pop(artifact_type, None)
        if start:
            elapsed_ms = (time.time() - start) * 1000
        if artifact_type not in self._metrics:
            self._metrics[artifact_type] = ArtifactMetrics(artifact_type=artifact_type)
        m = self._metrics[artifact_type]
        m.recompute_count += 1
        m.recompute_time_ms = round(elapsed_ms, 2)
        m.total_recompute_time_ms += elapsed_ms
        m.version = version
        m.last_updated = datetime.now(timezone.utc).isoformat()

    def record_cache_hit(self, artifact_type: str) -> None:
        if artifact_type not in self._metrics:
            self._metrics[artifact_type] = ArtifactMetrics(artifact_type=artifact_type)
        self._metrics[artifact_type].cache_hits += 1

    def record_cache_miss(self, artifact_type: str) -> None:
        if artifact_type not in self._metrics:
            self._metrics[artifact_type] = ArtifactMetrics(artifact_type=artifact_type)
        self._metrics[artifact_type].cache_misses += 1

    def get_system_metrics(
        self,
        cache_stats: Optional[Dict[str, Any]] = None,
        event_stats: Optional[Dict[str, Any]] = None,
        drift_report: Optional[Dict[str, Any]] = None,
        last_run: str = "",
    ) -> SystemMetrics:
        metrics = SystemMetrics()
        metrics.active_artifacts = len(self._metrics)
        metrics.last_pipeline_run = last_run
        metrics.system_uptime = self._format_uptime(time.time() - self._start_time)

        for m in self._metrics.values():
            metrics.total_recomputes += m.recompute_count
            metrics.total_cache_hits += m.cache_hits
            metrics.total_cache_misses += m.cache_misses

        if cache_stats:
            metrics.total_cache_invalidations = cache_stats.get("invalidations", 0)

        if event_stats:
            metrics.events_emitted = event_stats.get("total_events", 0)

        if drift_report:
            metrics.anti_drift_violations = drift_report.get("total_violations", 0)

        metrics.artifacts = dict(self._metrics)
        return metrics

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


_global_observability: Optional[ObservabilityCollector] = None


def get_observability() -> ObservabilityCollector:
    global _global_observability
    if _global_observability is None:
        _global_observability = ObservabilityCollector()
    return _global_observability
