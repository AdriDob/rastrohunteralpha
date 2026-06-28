"""
Core modules for Rastro.

Sub-packages:
  contracts/  — Canonical interfaces and base classes
  artifacts/  — Canonical artifact bundles (system-wide data objects)
  intelligence/ — Unification layer (dependency graph, events, cache, anti-drift)
  ... (existing engines remain unchanged)
"""

from core_engines.artifacts import (
    AIInsightArtifact,
    AttackSurfaceArtifact,
    DifferentialArtifact,
    EvidenceGraphArtifact,
    ExecutionPlanArtifact,
    HypothesisArtifact,
    PipelineArtifact,
    QuickWinsArtifact,
    ROIArtifact,
    ScreenshotArtifact,
)
from core_engines.contracts import Artifact, Bundle
from core_engines.intelligence import (
    AntiDriftEnforcer,
    ArtifactCache,
    DependencyGraph,
    EventSystem,
    UnifiedOrchestrator,
    get_orchestrator,
)
from core_engines.opportunity import (
    BaseProvider,
    HistoryManager,
    Opportunity,
    OpportunityCategory,
    OpportunityEngine,
    OpportunityRecommendations,
    OpportunityScore,
    OpportunitySnapshot,
    OpportunitySource,
    generate_recommendations,
    get_engine,
    get_history_manager,
    get_providers,
    score_opportunity,
)
