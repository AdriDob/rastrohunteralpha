"""
intelligence.unified_orchestrator — Central orchestrator for the Intelligence Unification Layer.

Coordinates:
- Artifact lifecycle (create, cache, invalidate)
- Event emission and subscription
- Dependency tracking
- Anti-drift enforcement
- Observability collection
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.contracts import ArtifactProtocol, InvalidationPolicy
from core.intelligence.cache import ArtifactCache, get_cache
from core.intelligence.dependency_graph import DependencyGraph
from core.intelligence.event_system import EventSystem, get_event_system
from core.intelligence.anti_drift import AntiDriftEnforcer, get_enforcer
from core.intelligence.observability import ObservabilityCollector, get_observability

LOG = logging.getLogger("rastro.intelligence.orchestrator")


class UnifiedOrchestrator:
    """
    Central orchestrator for artifact lifecycle management.

    Usage:
        orchestrator = UnifiedOrchestrator()
        artifact = orchestrator.compute("PipelineArtifact", pipeline_instance)
        cached = orchestrator.get("PipelineArtifact")
        orchestrator.invalidate("PipelineArtifact")
    """

    def __init__(
        self,
        cache: Optional[ArtifactCache] = None,
        event_system: Optional[EventSystem] = None,
        dependency_graph: Optional[DependencyGraph] = None,
        enforcer: Optional[AntiDriftEnforcer] = None,
        observability: Optional[ObservabilityCollector] = None,
    ) -> None:
        self.cache = cache or get_cache()
        self.events = event_system or get_event_system()
        self.dep_graph = dependency_graph or DependencyGraph()
        self.enforcer = enforcer or get_enforcer()
        self.observability = observability or get_observability()
        self._last_pipeline_run: str = ""

    def compute(
        self,
        artifact_type: str,
        engine_name: str,
        artifact: ArtifactProtocol,
        source_ids: Optional[List[str]] = None,
    ) -> ArtifactProtocol:
        """Register a computed artifact. Enforces ownership, caches, and emits events."""
        self.enforcer.check_write(engine_name, artifact_type)
        if source_ids:
            artifact.source_ids = list(set(artifact.source_ids + source_ids))
        self.observability.start_recompute(artifact_type)
        self.cache.set_artifact(artifact)
        self.observability.finish_recompute(artifact_type, artifact.version)
        event_map = {
            "PipelineArtifact": "PipelineUpdated",
            "AttackSurfaceArtifact": "AttackSurfaceUpdated",
            "ROIArtifact": "ROIUpdated",
            "HypothesisArtifact": "HypothesisUpdated",
            "EvidenceGraphArtifact": "EvidenceAdded",
            "QuickWinsArtifact": "QuickWinsUpdated",
            "ExecutionPlanArtifact": "ExecutionPlanUpdated",
            "ScreenshotArtifact": "ScreenshotUpdated",
            "DifferentialArtifact": "DifferentialUpdated",
            "AIInsightArtifact": "AIInsightUpdated",
        }
        event_type = event_map.get(artifact_type)
        if event_type:
            self.events.emit(event_type, {"artifact_type": artifact_type, "version": artifact.version})
        if artifact_type == "PipelineArtifact":
            from datetime import datetime, timezone
            self._last_pipeline_run = datetime.now(timezone.utc).isoformat()
        return artifact

    def get(self, artifact_type: str) -> Optional[ArtifactProtocol]:
        """Get a cached artifact by type name."""
        artifact = self.cache.get(artifact_type)
        if artifact:
            self.observability.record_cache_hit(artifact_type)
        else:
            self.observability.record_cache_miss(artifact_type)
        return artifact

    def invalidate(self, artifact_type: str) -> List[str]:
        """Invalidate an artifact and all its dependents. Returns affected types."""
        self.cache.invalidate(artifact_type)
        affected = self.dep_graph.affected_by(artifact_type)
        if affected:
            self.cache.invalidate_many(affected)
        self.events.emit("ArtifactInvalidated", {
            "artifact_type": artifact_type,
            "affected": affected,
        })
        return affected

    def get_or_compute(
        self,
        artifact_type: str,
        engine_name: str,
        compute_fn,
        force: bool = False,
        source_ids: Optional[List[str]] = None,
    ) -> ArtifactProtocol:
        """Get from cache or compute if missing/invalidated."""
        if not force:
            cached = self.get(artifact_type)
            if cached is not None:
                return cached
        artifact = compute_fn()
        return self.compute(artifact_type, engine_name, artifact, source_ids)

    def stats(self) -> Dict[str, Any]:
        """Get system-wide statistics."""
        cache_stats = self.cache.stats()
        event_stats = self.events.stats()
        drift_report = self.enforcer.report()
        system_metrics = self.observability.get_system_metrics(
            cache_stats=cache_stats,
            event_stats=event_stats,
            drift_report=drift_report,
            last_run=self._last_pipeline_run,
        )
        dep_graph_info = self.dep_graph.to_dict()
        return {
            "metrics": system_metrics.to_dict(),
            "cache": cache_stats,
            "events": event_stats,
            "anti_drift": drift_report,
            "dependency_graph": {
                "valid": dep_graph_info.get("valid", False),
                "execution_order": dep_graph_info.get("execution_order", []),
            },
            "artifacts_available": list(self.cache._store.keys()) if hasattr(self.cache, '_store') else [],
        }

    def get_execution_order(self) -> List[str]:
        return self.dep_graph.execution_order()

    def get_affected_by(self, artifact_type: str) -> List[str]:
        return self.dep_graph.affected_by(artifact_type)

    def emit_event(self, event_type: str, payload: Any = None) -> None:
        self.events.emit(event_type, payload)


_global_orchestrator: Optional[UnifiedOrchestrator] = None


def get_orchestrator() -> UnifiedOrchestrator:
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = UnifiedOrchestrator()
    return _global_orchestrator
