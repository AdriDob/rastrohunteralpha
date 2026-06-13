"""
intelligence.pipeline_integration — Integration between the pipeline and the unification layer.

Provides hooks that:
1. Convert pipeline output into canonical artifacts
2. Register artifacts with the orchestrator
3. Emit events for downstream consumers
4. Enable incremental recomputation

This is called AFTER the pipeline completes, NOT during pipeline execution.
The pipeline itself is not modified.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.artifacts import (
    PipelineArtifact,
    EvidenceGraphArtifact,
    AttackSurfaceArtifact,
    ROIArtifact,
    HypothesisArtifact,
    QuickWinsArtifact,
    ScreenshotArtifact,
    DifferentialArtifact,
    AIInsightArtifact,
    ExecutionPlanArtifact,
)
from core.intelligence.unified_orchestrator import get_orchestrator
from core.intelligence.event_system import get_event_system

LOG = logging.getLogger("rastro.intelligence.integration")


class PipelineIntegration:
    """
    Integration hooks for the pipeline.

    Call these after the pipeline finishes to register artifacts.
    """

    @staticmethod
    def register_pipeline(pipeline_result: Dict[str, Any]) -> PipelineArtifact:
        """Register the PipelineSnapshot as a canonical artifact."""
        snapshot = pipeline_result.get("snapshot")
        if snapshot is None:
            from core.engine.snapshot import from_pipeline_output
            snapshot = from_pipeline_output(pipeline_result)
        artifact = PipelineArtifact.from_snapshot(snapshot)
        orch = get_orchestrator()
        orch.compute("PipelineArtifact", "Pipeline", artifact)
        LOG.info("PipelineArtifact registered (status=%s, endpoints=%d)",
                 artifact.status, artifact.endpoint_count)
        return artifact

    @staticmethod
    def register_attack_surface(surface_map) -> AttackSurfaceArtifact:
        """Register the attack surface mapping as a canonical artifact."""
        from core.engine.risk_model import AttackSurfaceMap
        artifact = AttackSurfaceArtifact.from_surface_map(surface_map)
        orch = get_orchestrator()
        orch.compute("AttackSurfaceArtifact", "AttackSurfaceMapper", artifact)
        return artifact

    @staticmethod
    def register_roi(roi_data: Dict[str, Any]) -> ROIArtifact:
        """Register ROI data as a canonical artifact."""
        artifact = ROIArtifact(endpoint_rois=roi_data.get("by_endpoint", {}))
        orch = get_orchestrator()
        orch.compute("ROIArtifact", "ROI Engine", artifact)
        return artifact

    @staticmethod
    def register_hypotheses(hypothesis_output) -> HypothesisArtifact:
        """Register hypothesis output as a canonical artifact."""
        artifact = HypothesisArtifact.from_engine_output(hypothesis_output)
        orch = get_orchestrator()
        orch.compute("HypothesisArtifact", "Hypothesis Engine", artifact)
        return artifact

    @staticmethod
    def register_evidence(evidence_graph) -> EvidenceGraphArtifact:
        """Register the evidence graph as a canonical artifact."""
        artifact = EvidenceGraphArtifact.from_graph(evidence_graph)
        orch = get_orchestrator()
        orch.compute("EvidenceGraphArtifact", "Evidence Builder", artifact)
        return artifact

    @staticmethod
    def register_quick_wins(quick_wins_report) -> QuickWinsArtifact:
        """Register quick wins as a canonical artifact."""
        artifact = QuickWinsArtifact.from_report(quick_wins_report)
        orch = get_orchestrator()
        orch.compute("QuickWinsArtifact", "Quick Wins Engine", artifact)
        return artifact

    @staticmethod
    def register_screenshot(screenshot_bundle) -> ScreenshotArtifact:
        """Register screenshot bundle as a canonical artifact."""
        artifact = ScreenshotArtifact.from_bundle(screenshot_bundle)
        orch = get_orchestrator()
        orch.compute("ScreenshotArtifact", "Screenshot Engine", artifact)
        return artifact

    @staticmethod
    def register_differential(differential_bundle) -> DifferentialArtifact:
        """Register differential bundle as a canonical artifact."""
        artifact = DifferentialArtifact.from_bundle(differential_bundle)
        orch = get_orchestrator()
        orch.compute("DifferentialArtifact", "Differential Intelligence Engine", artifact)
        return artifact

    @staticmethod
    def register_ai_insights(insight_artifact: AIInsightArtifact) -> AIInsightArtifact:
        """Register AI insights as a canonical artifact."""
        orch = get_orchestrator()
        orch.compute("AIInsightArtifact", "AI Assistant", insight_artifact)
        return insight_artifact

    @staticmethod
    def register_execution_plan(plan: ExecutionPlanArtifact) -> ExecutionPlanArtifact:
        """Register execution plan as a canonical artifact."""
        orch = get_orchestrator()
        orch.compute("ExecutionPlanArtifact", "Execution Hardening Layer", plan)
        return plan

    @staticmethod
    def register_all_from_pipeline(
        pipeline_result: Dict[str, Any],
        evidence_graph=None,
        surface_map=None,
        hypothesis_output=None,
    ) -> Dict[str, Any]:
        """
        Convenience method: register all possible artifacts from a pipeline result.
        Returns a dict of registered artifact types.
        """
        registered: Dict[str, Any] = {}

        pipeline_artifact = PipelineIntegration.register_pipeline(pipeline_result)
        registered["PipelineArtifact"] = pipeline_artifact

        if surface_map:
            registered["AttackSurfaceArtifact"] = PipelineIntegration.register_attack_surface(surface_map)

        if evidence_graph:
            registered["EvidenceGraphArtifact"] = PipelineIntegration.register_evidence(evidence_graph)

        if hypothesis_output:
            registered["HypothesisArtifact"] = PipelineIntegration.register_hypotheses(hypothesis_output)

        es = get_event_system()
        es.emit("PipelineUpdated", {
            "status": pipeline_result.get("status"),
            "artifact_types": list(registered.keys()),
        })

        LOG.info("Registered %d artifacts from pipeline run", len(registered))
        return registered
