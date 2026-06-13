"""
Core modules for Rastro.

Sub-packages:
  contracts/  — Canonical interfaces and base classes
  artifacts/  — Canonical artifact bundles (system-wide data objects)
  intelligence/ — Unification layer (dependency graph, events, cache, anti-drift)
  ... (existing engines remain unchanged)
"""

from core.contracts import Artifact, Bundle
from core.artifacts import (
    PipelineArtifact, EvidenceGraphArtifact, ScreenshotArtifact,
    DifferentialArtifact, QuickWinsArtifact, ExecutionPlanArtifact,
    AIInsightArtifact, AttackSurfaceArtifact, ROIArtifact, HypothesisArtifact,
)
from core.intelligence import (
    DependencyGraph, EventSystem, ArtifactCache, AntiDriftEnforcer,
    UnifiedOrchestrator, get_orchestrator,
)
from core.opportunity import (
    Opportunity, OpportunitySource, OpportunityCategory,
    OpportunityScore, OpportunitySnapshot, OpportunityRecommendations,
    OpportunityEngine, get_engine,
    BaseProvider, get_providers,
    score_opportunity,
    generate_recommendations,
    HistoryManager, get_history_manager,
)
