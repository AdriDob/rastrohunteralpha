"""
Opportunity Intelligence Layer — read-only public opportunity discovery and prioritization.

Never modifies pipeline data. All outputs are metadata and recommendations.
Supports advanced layered scoring, EVH, and identity vault integration.
"""

from core_engines.opportunity.models import (
    EVHCalculation,
    EVHRating,
    Opportunity,
    OpportunitySource,
    OpportunityCategory,
    OpportunityScore,
    ScoreBreakdown,
    OpportunitySnapshot,
    OpportunityProviderInfo,
    OpportunityRecommendations,
    IdentityVaultEntry,
)
from core_engines.opportunity.engine import OpportunityEngine, get_engine
from core_engines.opportunity.providers import (
    BaseProvider,
    get_providers,
    ManualProvider,
    PublicProgramProvider,
    GitHubAdvisoryProvider,
    HuntrProvider,
    AllSourcesProvider,
)
from core_engines.opportunity.scoring import score_opportunity as score_legacy
from core_engines.opportunity.scoring2 import compute_layered_score, compute_evh, _score_to_priority
from core_engines.opportunity.recommendations import generate_recommendations
from core_engines.opportunity.history import HistoryManager, get_history_manager

# Backward-compatible alias
score_opportunity = score_legacy

__all__ = [
    "Opportunity", "OpportunitySource", "OpportunityCategory",
    "OpportunityScore", "ScoreBreakdown", "OpportunitySnapshot",
    "OpportunityProviderInfo", "OpportunityRecommendations",
    "EVHCalculation", "EVHRating", "IdentityVaultEntry",
    "OpportunityEngine", "get_engine",
    "BaseProvider", "get_providers",
    "ManualProvider", "PublicProgramProvider",
    "GitHubAdvisoryProvider", "HuntrProvider", "AllSourcesProvider",
    "score_legacy", "compute_layered_score", "compute_evh", "_score_to_priority",
    "generate_recommendations",
    "HistoryManager", "get_history_manager",
]
