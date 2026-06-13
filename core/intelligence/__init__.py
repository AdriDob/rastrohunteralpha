"""
Core intelligence modules for Rastro.

Sub-packages:
  Unification layer: dependency_graph, event_system, cache, anti_drift
  Learning layer: adaptive_memory, pattern_registry, historical_analyzer,
                  trend_detector, recommendation_engine, learning_snapshot
"""

from core.intelligence.dependency_graph import DependencyGraph
from core.intelligence.event_system import EventSystem
from core.intelligence.cache import ArtifactCache
from core.intelligence.anti_drift import AntiDriftEnforcer
from core.intelligence.unified_orchestrator import UnifiedOrchestrator, get_orchestrator
from core.intelligence.adaptive_memory import AdaptiveMemory, get_memory, reset_memory
from core.intelligence.pattern_registry import PatternRegistry, PatternStats, get_registry, reset_registry
from core.intelligence.historical_analyzer import HistoricalSummary, analyze_historical_data
from core.intelligence.trend_detector import TrendReport, TrendSignal, detect_trends
from core.intelligence.recommendation_engine import RecommendationBundle, generate_recommendations
from core.intelligence.learning_snapshot import LearningSnapshot, generate_snapshot

__all__ = [
    "DependencyGraph", "EventSystem", "ArtifactCache", "AntiDriftEnforcer",
    "UnifiedOrchestrator", "get_orchestrator",
    "AdaptiveMemory", "get_memory", "reset_memory",
    "PatternRegistry", "PatternStats", "get_registry", "reset_registry",
    "HistoricalSummary", "analyze_historical_data",
    "TrendReport", "TrendSignal", "detect_trends",
    "RecommendationBundle", "generate_recommendations",
    "LearningSnapshot", "generate_snapshot",
]
