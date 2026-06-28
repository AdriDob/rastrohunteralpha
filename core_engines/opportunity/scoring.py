"""Opportunity scoring engine — computes multi-factor priority scores.

All factors are estimates based on public information.
Never invents values. Unknown information remains unknown.
"""

from __future__ import annotations

import logging

from core_engines.opportunity.models import Opportunity, OpportunityScore

logger = logging.getLogger("rastro.opportunity.scoring")

# Known high-value technology keywords
_HIGH_VALUE_TAGS: set[str] = {
    "cloud", "aws", "gcp", "azure", "kubernetes", "docker",
    "api", "graphql", "rest", "oauth", "saml", "jwt",
    "mobile", "ios", "android", "react-native", "flutter",
    "web3", "solidity", "defi", "rust", "move",
    "hardware", "firmware", "iot", "bluetooth",
}

# Keywords that suggest larger scope
_SCOPE_KEYWORDS: set[str] = {
    "all", "full", "wide", "entire", "comprehensive",
    "thousands", "hundreds", "multiple", "extensive",
    "global", "enterprise", "platform",
}

# Source confidence weights
_SOURCE_CONFIDENCE_WEIGHT = 0.1


def score_opportunity(
    opp: Opportunity,
    operator_tags: list[str] | None = None,
    pattern_overlap: float = 0.0,
) -> OpportunityScore:
    """Compute a multi-factor OpportunityScore for a single opportunity.

    Factors:
      - reward_potential: estimated financial or non-financial value
      - scope_quality: breadth of the attack surface described
      - technology_overlap: how well the tech stack matches operator preferences
      - competition_estimate: how many researchers are likely competing
      - freshness: how recently the program was updated

    Returns an OpportunityScore with overall 0.0-1.0 and reasoning.
    """
    reasoning: list[str] = []

    # ── Reward potential (0.0-1.0) ──────────────────────────────────
    reward = _score_reward(opp)
    reasoning.append(f"Reward potential: {reward:.2f}")

    # ── Scope quality (0.0-1.0) ─────────────────────────────────────
    scope = _score_scope(opp)
    reasoning.append(f"Scope quality: {scope:.2f}")

    # ── Technology overlap (0.0-1.0) ────────────────────────────────
    tech = _score_technology(opp, operator_tags or [])
    reasoning.append(f"Technology overlap: {tech:.2f}")

    # ── Competition estimate (0.0-1.0, higher = less competition) ───
    competition = _score_competition(opp)
    reasoning.append(f"Competition estimate (higher = less contested): {competition:.2f}")

    # ── Freshness (0.0-1.0) ─────────────────────────────────────────
    freshness = _score_freshness(opp)
    reasoning.append(f"Freshness: {freshness:.2f}")

    # ── Weighted overall ────────────────────────────────────────────
    weights = {
        "reward": 0.25,
        "scope": 0.15,
        "tech": 0.20,
        "competition": 0.20,
        "freshness": 0.10,
        "source_confidence": 0.10,
    }

    overall = (
        weights["reward"] * reward
        + weights["scope"] * scope
        + weights["tech"] * tech
        + weights["competition"] * competition
        + weights["freshness"] * freshness
        + weights["source_confidence"] * opp.source.confidence
    )

    overall = max(0.0, min(1.0, overall))

    return OpportunityScore(
        overall=round(overall, 4),
        reward_potential=round(reward, 4),
        scope_quality=round(scope, 4),
        technology_overlap=round(tech, 4),
        competition_estimate=round(competition, 4),
        freshness=round(freshness, 4),
        reasoning=reasoning,
    )


def _score_reward(opp: Opportunity) -> float:
    """Estimate reward potential from public reward info."""
    text = (opp.reward_info or "").lower()

    # Keywords suggesting financial rewards
    high_value = ["$1,000,000", "$500,000", "$100,000", "million"]
    medium_value = ["$10,000", "$5,000", "$1,000", "p50", "p30", "bounty"]
    low_value = ["vdp", "recognition", "swag", "acknowledgment", "hall of fame"]
    unknown = ["unknown", "none", "varies"]

    if any(kw in text for kw in high_value):
        return 0.95
    if any(kw in text for kw in medium_value):
        return 0.7
    if any(kw in text for kw in low_value):
        return 0.3
    if any(kw in text for kw in unknown):
        return 0.2

    # Platform programs more likely to have rewards
    if opp.category == "platform":
        return 0.5
    if opp.category == "web3":
        return 0.6
    if opp.category == "emerging":
        return 0.3
    if opp.category == "research":
        return 0.1

    return 0.3


def _score_scope(opp: Opportunity) -> float:
    """Estimate scope size and quality from scope_summary."""
    text = (opp.scope_summary or "").lower()
    score = 0.3  # baseline

    keyword_match = sum(1 for kw in _SCOPE_KEYWORDS if kw in text)
    score += keyword_match * 0.1

    if "public" in text:
        score += 0.15
    if "private" in text:
        score -= 0.05

    tags = opp.technology_tags
    if len(tags) >= 4:
        score += 0.1
    elif len(tags) >= 2:
        score += 0.05

    return max(0.0, min(1.0, score))


def _score_technology(opp: Opportunity, operator_tags: list[str]) -> float:
    """Measure technology overlap with operator preferences."""
    opp_tags = set(t.lower() for t in opp.technology_tags)
    op_tags = set(t.lower() for t in operator_tags)

    if not opp_tags:
        return 0.3
    if not op_tags:
        # No operator preferences — score based on general value
        high_value_count = sum(1 for t in opp_tags if t in _HIGH_VALUE_TAGS)
        return min(1.0, 0.3 + high_value_count * 0.1)

    intersection = opp_tags & op_tags
    union = opp_tags | op_tags

    if not union:
        return 0.3

    jaccard = len(intersection) / len(union)
    return min(1.0, 0.2 + jaccard * 0.8)


def _score_competition(opp: Opportunity) -> float:
    """Estimate competition level.

    Higher score = less competition (more favourable).
    """
    name_lower = opp.name.lower()

    # Major platforms — high competition
    if any(platform in name_lower for platform in ["hackerone", "bugcrowd", "intigriti"]):
        return 0.3

    # Well-known aggregator — still high competition
    if "disclose" in name_lower:
        return 0.5

    # Web3 platforms — currently high interest
    if opp.category == "web3":
        return 0.35

    # Independent — potentially lower competition
    if opp.category == "independent":
        return 0.65

    # Emerging or research — lowest competition
    if opp.category in ("emerging", "research"):
        return 0.8

    return 0.5


def _score_freshness(opp: Opportunity) -> float:
    """Score based on recency of last update.

    Recently updated programs = more active = more opportunity.
    """
    if not opp.last_update:
        # No freshness info — neutral
        return 0.5

    # Try to parse ISO timestamp
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(opp.last_update)
        now = datetime.now(timezone.utc)
        days_ago = (now - dt).days

        if days_ago < 7:
            return 0.95
        if days_ago < 30:
            return 0.8
        if days_ago < 90:
            return 0.6
        if days_ago < 180:
            return 0.4
        return 0.2
    except (ValueError, TypeError):
        return 0.5
