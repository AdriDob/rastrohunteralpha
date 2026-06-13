"""
core.engine.hypothesis — Rastro's Hypothesis Engine.

Converts attack surface data into actionable vulnerability hypotheses
organized in a prioritized attack queue.

Data flow:
  scored_endpoints → rule generators → memory refinement → LLM enrichment → attack_queue

Key components:
  engine.HypothesisEngine — main orchestrator
  models.Hypothesis — vulnerability hypothesis data model
  models.AttackQueue — prioritized queue of hypotheses
  generators — 9 rule-based hypothesis generators (idor, auth_bypass, ssrf, etc.)
  scorer — likelihood/impact/exploitability/confidence scoring
  memory — past finding-based hypothesis refinement
  llm — optional LLM reasoning enrichment (NOT scanning)
"""

from core.engine.hypothesis.engine import HypothesisEngine
from core.engine.hypothesis.models import (
    AttackQueue,
    Hypothesis,
    HypothesisEngineOutput,
    HypothesisScore,
    HypothesisSource,
    VulnerabilityType,
)

__all__ = [
    "HypothesisEngine",
    "AttackQueue",
    "Hypothesis",
    "HypothesisEngineOutput",
    "HypothesisScore",
    "HypothesisSource",
    "VulnerabilityType",
]
