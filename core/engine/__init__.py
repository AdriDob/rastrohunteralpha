"""
core.engine — Rastro's unified intelligence engine.

Single source of truth for all scoring, classification, and risk modeling.

Modules:
  unified_scoring    → score(), score_target(), generate_suggestions()
  unified_classifier → classify(), synthesize_target_meta()
  risk_model         → NoiseReductionLayer, RiskClassifier, AttackSurfaceMapper,
                       ROIEstimator, analyze()
  hypothesis         → HypothesisEngine, Hypothesis, AttackQueue
  snapshot           → PipelineSnapshot (immutable reporting format)
  guardrails         → Architectural enforcement
"""

from core.engine.unified_scoring import score, score_target, generate_suggestions
from core.engine.unified_classifier import classify, synthesize_target_meta
from core.engine.snapshot import PipelineSnapshot, from_pipeline_output
from core.engine.hypothesis import HypothesisEngine, Hypothesis, AttackQueue, VulnerabilityType

__all__ = [
    "score",
    "score_target",
    "classify",
    "synthesize_target_meta",
    "generate_suggestions",
    "PipelineSnapshot",
    "from_pipeline_output",
    "HypothesisEngine",
    "Hypothesis",
    "AttackQueue",
    "VulnerabilityType",
]
