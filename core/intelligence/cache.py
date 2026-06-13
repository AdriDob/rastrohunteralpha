"""
intelligence.cache — Smart cache layer for artifact storage and invalidation.

Prevents recalculation when input data has not changed.
Each artifact declares its dependencies, version, and source_ids for invalidation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.contracts import ArtifactProtocol, CacheProtocol, InvalidationPolicy

LOG = logging.getLogger("rastro.intelligence.cache")

AFFECTED_BY_CHANGE: Dict[str, List[str]] = {
    "PipelineArtifact": [
        "AttackSurfaceArtifact", "ROIArtifact", "HypothesisArtifact",
        "EvidenceGraphArtifact", "QuickWinsArtifact", "ExecutionPlanArtifact",
        "ScreenshotArtifact", "DifferentialArtifact", "AIInsightArtifact",
    ],
    "AttackSurfaceArtifact": [
        "ROIArtifact", "HypothesisArtifact", "DifferentialArtifact", "AIInsightArtifact",
    ],
    "ROIArtifact": [
        "HypothesisArtifact", "AIInsightArtifact",
    ],
    "HypothesisArtifact": [
        "DifferentialArtifact", "AIInsightArtifact",
    ],
    "EvidenceGraphArtifact": [
        "QuickWinsArtifact", "ExecutionPlanArtifact",
        "ScreenshotArtifact", "DifferentialArtifact", "AIInsightArtifact",
    ],
    "QuickWinsArtifact": [
        "ExecutionPlanArtifact", "AIInsightArtifact",
    ],
    "ExecutionPlanArtifact": [
        "AIInsightArtifact",
    ],
    "ScreenshotArtifact": [
        "DifferentialArtifact", "AIInsightArtifact",
    ],
    "DifferentialArtifact": [
        "AIInsightArtifact",
    ],
    "AIInsightArtifact": [],
}


class ArtifactCache:
    """
    Cache for computed artifacts.

    Each artifact is keyed by its type name (e.g., "PipelineArtifact").
    The cache tracks versions, timestamps, and source_ids for invalidation.
    """

    def __init__(self) -> None:
        self._store: Dict[str, ArtifactProtocol] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._invalidations: int = 0

    def get(self, key: str) -> Optional[ArtifactProtocol]:
        artifact = self._store.get(key)
        if artifact is not None:
            self._hits += 1
            return artifact
        self._misses += 1
        return None

    def set(self, key: str, artifact: ArtifactProtocol) -> None:
        self._store[key] = artifact

    def invalidate(self, key: str) -> None:
        if key in self._store:
            del self._store[key]
            self._invalidations += 1
            LOG.debug("Invalidated cache: %s", key)

    def invalidate_many(self, keys: List[str]) -> None:
        for key in keys:
            self.invalidate(key)

    def invalidate_related(self, changed_artifact: str) -> List[str]:
        affected = AFFECTED_BY_CHANGE.get(changed_artifact, [])
        self.invalidate_many(affected)
        return affected

    def clear(self) -> None:
        self._store.clear()
        self._hits = 0
        self._misses = 0
        self._invalidations = 0

    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "cached_artifacts": list(self._store.keys()),
            "cached_count": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / max(total, 1), 4),
            "invalidations": self._invalidations,
        }

    def get_artifact(self, artifact_type: str) -> Optional[ArtifactProtocol]:
        return self.get(artifact_type)

    def set_artifact(self, artifact: ArtifactProtocol) -> None:
        key = type(artifact).__name__
        self.set(key, artifact)

    def invalidate_by_policy(
        self,
        policy: InvalidationPolicy,
        artifact_type: str,
        changed_sources: Optional[List[str]] = None,
    ) -> bool:
        """
        Check if an artifact should be invalidated based on policy.
        Returns True if invalidated.
        """
        artifact = self.get(artifact_type)
        if artifact is None:
            return False

        if policy.force_recompute:
            self.invalidate(artifact_type)
            return True

        if policy.max_age_seconds is not None:
            from datetime import datetime
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(artifact.timestamp)).total_seconds()
                if age > policy.max_age_seconds:
                    self.invalidate(artifact_type)
                    return True
            except (ValueError, TypeError):
                pass

        if policy.dependencies_changed and changed_sources:
            current_sources = set(artifact.source_ids)
            if any(s in changed_sources for s in current_sources):
                self.invalidate(artifact_type)
                return True

        return False


_global_cache: Optional[ArtifactCache] = None


def get_cache() -> ArtifactCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = ArtifactCache()
    return _global_cache
