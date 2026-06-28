"""Data models for the Opportunity Intelligence Layer — read-only metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EVHRating(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


@dataclass(frozen=True)
class OpportunitySource:
    """Origin metadata for an opportunity."""
    type: str  # "platform", "independent", "web3", "emerging", "research"
    name: str
    url: str
    confidence: float  # 0.0-1.0


@dataclass(frozen=True)
class OpportunityCategory:
    """Categorisation of the opportunity's technical domain."""
    primary: str  # web, api, mobile, web3, cloud, hardware, other
    secondary: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoreBreakdown:
    """Detailed layered score with per-factor explanation."""
    reward_score: float
    competition_score: float
    discovery_score: float
    execution_score: float
    intelligence_score: float
    strategic_score: float
    confidence_score: float
    reward_explanation: str = ""
    competition_explanation: str = ""
    discovery_explanation: str = ""
    execution_explanation: str = ""
    intelligence_explanation: str = ""
    strategic_explanation: str = ""
    confidence_explanation: str = ""


@dataclass(frozen=True)
class EVHCalculation:
    """Expected Value Per Hour estimate."""
    value: float
    rating: EVHRating
    estimated_payout: float
    success_probability: float
    estimated_effort_hours: float
    explanation: str = ""


@dataclass(frozen=True)
class OpportunityScore:
    """Computed multi-factor score with human-readable reasoning."""
    overall: float  # 0.0-1.0
    reward_potential: float
    scope_quality: float
    technology_overlap: float
    competition_estimate: float
    freshness: float
    reasoning: list[str]
    breakdown: ScoreBreakdown | None = None
    evh: EVHCalculation | None = None


@dataclass(frozen=True)
class Opportunity:
    """A single public bug bounty or responsible disclosure opportunity."""
    id: str
    name: str
    source: OpportunitySource
    category: str  # "platform", "independent", "web3", "emerging", "research", "ai", "infrastructure", "cloud", "mobile", "browser_extension", "api_ecosystem", "open_source", "paid_research"
    subcategory: str = ""  # more granular classification
    public_url: str | None = None
    scope_summary: str | None = None
    reward_info: str | None = None
    technology_tags: list[str] = field(default_factory=list)
    last_update: str | None = None
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    score: OpportunityScore | None = None
    priority: str | None = None  # critical, high, medium, low
    created_at: str = ""
    estimated_payout: float = 0.0
    estimated_effort_hours: float = 1.0
    has_rewards: bool = True


@dataclass(frozen=True)
class OpportunitySnapshot:
    """Point-in-time snapshot of all tracked opportunities."""
    id: str
    timestamp: str
    period: str  # daily, weekly, monthly
    opportunities: list[Opportunity] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OpportunityProviderInfo:
    """Describes a registered provider."""
    name: str
    category: str
    active: bool
    opportunity_count: int
    last_refresh: str | None = None
    health_status: str = "unknown"  # healthy, degraded, down


@dataclass(frozen=True)
class OpportunityRecommendations:
    """Generated operator recommendations."""
    top_opportunities: list[Opportunity] = field(default_factory=list)
    top_independent: list[Opportunity] = field(default_factory=list)
    top_web3: list[Opportunity] = field(default_factory=list)
    fast_roi: list[Opportunity] = field(default_factory=list)
    long_term: list[Opportunity] = field(default_factory=list)
    low_competition: list[Opportunity] = field(default_factory=list)
    evh_ranked: list[Opportunity] = field(default_factory=list)
    generated_at: str = ""
    summary: str = ""


@dataclass(frozen=True)
class IdentityVaultEntry:
    """Stored provider identity."""
    provider_name: str
    email: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    session_state: str = "disconnected"  # connected, disconnected, expired
    last_checked: str | None = None
    health_status: str = "unknown"
