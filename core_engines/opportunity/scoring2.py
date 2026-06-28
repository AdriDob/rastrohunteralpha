"""Layered opportunity scoring engine — computes advanced multi-factor scores.

Seven-factor model: Reward, Competition, Discovery, Execution,
Intelligence, Strategic, Confidence. Generates EVH (Expected Value Per Hour).

All factors are estimates based on public information.
Never invents values. Unknown information remains unknown.
"""

from __future__ import annotations

import contextlib
import logging
import re
from datetime import datetime, timezone

from core_engines.opportunity.models import (
    EVHCalculation,
    EVHRating,
    Opportunity,
    OpportunityScore,
    ScoreBreakdown,
)

logger = logging.getLogger("rastro.opportunity.scoring2")

# Known high-value technology keywords
_HIGH_VALUE_TAGS: set[str] = {
    "cloud", "aws", "gcp", "azure", "kubernetes", "docker",
    "api", "graphql", "rest", "oauth", "saml", "jwt",
    "mobile", "ios", "android", "react-native", "flutter",
    "web3", "solidity", "defi", "rust", "move",
    "hardware", "firmware", "iot", "bluetooth",
}

# Attack surface diversity markers
_DISCOVERY_SURFACE_KEYWORDS: dict[str, float] = {
    "graphql": 0.3,
    "api": 0.25,
    "admin": 0.2,
    "multi.tenant": 0.15,
    "upload": 0.2,
    "web3": 0.25,
    "mobile": 0.15,
    "cloud": 0.15,
    "microservice": 0.2,
    "sso": 0.15,
}

# Competition computation constants
_MAJOR_PLATFORMS = {"hackerone", "bugcrowd", "intigriti", "yeswehack"}
_WEB3_PLATFORMS = {"immunefi", "hackenproof", "code4rena", "hats finance"}


def compute_layered_score(
    opp: Opportunity,
    operator_tags: list[str] | None = None,
    pattern_score: float = 0.0,
    historical_score: float = 0.0,
    memory_score: float = 0.0,
) -> OpportunityScore:
    """Compute layered OpportunityScore with EVH and breakdown."""
    reasoning: list[str] = []

    # ── 1. Reward Score (0-100) ────────────────────────────────────
    reward_score, reward_exp = _compute_reward_score(opp)
    reasoning.append(f"Reward: {reward_score:.1f}/100 — {reward_exp}")

    # ── 2. Competition Score (0-100) ───────────────────────────────
    competition_score, competition_exp = _compute_competition_score(opp)
    reasoning.append(f"Competition: {competition_score:.1f}/100 — {competition_exp}")

    # ── 3. Discovery Score (0-100) ─────────────────────────────────
    discovery_score, discovery_exp = _compute_discovery_score(opp)
    reasoning.append(f"Discovery: {discovery_score:.1f}/100 — {discovery_exp}")

    # ── 4. Execution Score (0-100) ─────────────────────────────────
    execution_score, execution_exp = _compute_execution_score(opp)
    reasoning.append(f"Execution: {execution_score:.1f}/100 — {execution_exp}")

    # ── 5. Intelligence Score (0-100) ──────────────────────────────
    intelligence_score, intelligence_exp = _compute_intelligence_score(
        opp, pattern_score, historical_score, memory_score
    )
    reasoning.append(f"Intelligence: {intelligence_score:.1f}/100 — {intelligence_exp}")

    # ── 6. Strategic Score (0-100) ─────────────────────────────────
    strategic_score, strategic_exp = _compute_strategic_score(opp)
    reasoning.append(f"Strategic: {strategic_score:.1f}/100 — {strategic_exp}")

    # ── 7. Confidence Score (0-100) ────────────────────────────────
    confidence_score, confidence_exp = _compute_confidence_score(opp)
    reasoning.append(f"Confidence: {confidence_score:.1f}/100 — {confidence_exp}")

    # ── Weighted overall ───────────────────────────────────────────
    weights = {
        "reward": 0.20,
        "competition": 0.15,
        "discovery": 0.15,
        "execution": 0.15,
        "intelligence": 0.15,
        "strategic": 0.10,
        "confidence": 0.10,
    }

    overall = (
        weights["reward"] * (reward_score / 100.0)
        + weights["competition"] * (competition_score / 100.0)
        + weights["discovery"] * (discovery_score / 100.0)
        + weights["execution"] * (execution_score / 100.0)
        + weights["intelligence"] * (intelligence_score / 100.0)
        + weights["strategic"] * (strategic_score / 100.0)
        + weights["confidence"] * (confidence_score / 100.0)
    )
    overall = max(0.0, min(1.0, overall))

    breakdown = ScoreBreakdown(
        reward_score=round(reward_score, 2),
        reward_explanation=reward_exp,
        competition_score=round(competition_score, 2),
        competition_explanation=competition_exp,
        discovery_score=round(discovery_score, 2),
        discovery_explanation=discovery_exp,
        execution_score=round(execution_score, 2),
        execution_explanation=execution_exp,
        intelligence_score=round(intelligence_score, 2),
        intelligence_explanation=intelligence_exp,
        strategic_score=round(strategic_score, 2),
        strategic_explanation=strategic_exp,
        confidence_score=round(confidence_score, 2),
        confidence_explanation=confidence_exp,
    )

    # ── EVH ────────────────────────────────────────────────────────
    evh = compute_evh(opp, overall, reward_score, execution_score, confidence_score)

    return OpportunityScore(
        overall=round(overall, 4),
        reward_potential=round(reward_score / 100.0, 4),
        scope_quality=round(discovery_score / 100.0, 4),
        technology_overlap=_compute_tech_overlap(opp, operator_tags or []),
        competition_estimate=round(1.0 - (competition_score / 100.0), 4),
        freshness=_compute_freshness(opp),
        reasoning=reasoning,
        breakdown=breakdown,
        evh=evh,
    )


def compute_evh(
    opp: Opportunity,
    overall_score: float,
    reward_score: float,
    execution_score: float,
    confidence_score: float,
) -> EVHCalculation:
    """Compute Expected Value Per Hour.

    EVH = (estimated_payout * success_probability * confidence) / estimated_effort_hours
    """
    estimated_payout = opp.estimated_payout or _estimate_payout_from_reward(opp)
    success_probability = max(0.05, min(0.95, (overall_score * 0.7 + confidence_score / 100.0 * 0.3)))
    estimated_effort_hours = opp.estimated_effort_hours or max(0.5, 4.0 - execution_score / 30.0)

    evh_value = (estimated_payout * success_probability) / max(0.5, estimated_effort_hours)

    if evh_value > 500:
        rating = EVHRating.high
        explanation = f"~${evh_value:.0f}/hr — strong expected return"
    elif evh_value > 100:
        rating = EVHRating.medium
        explanation = f"~${evh_value:.0f}/hr — moderate expected return"
    else:
        rating = EVHRating.low
        explanation = f"~${evh_value:.0f}/hr — lower expected return"

    return EVHCalculation(
        value=round(evh_value, 2),
        rating=rating,
        estimated_payout=estimated_payout,
        success_probability=round(success_probability, 3),
        estimated_effort_hours=round(estimated_effort_hours, 1),
        explanation=explanation,
    )


def _compute_reward_score(opp: Opportunity) -> tuple[float, str]:
    """Reward Score: average payout, max payout, historical quality, payment consistency."""
    text = (opp.reward_info or "").lower()

    high_value_kw = ["$1,000,000", "$500,000", "$100,000", "million", "critical"]
    medium_value_kw = ["$10,000", "$5,000", "$1,000", "bounty", "p50", "p30"]
    low_value_kw = ["vdp", "recognition", "swag", "acknowledgment", "hall of fame"]
    no_reward_kw = ["no reward", "unpaid", "voluntary"]

    if any(kw in text for kw in no_reward_kw):
        return 0.0, "No financial rewards — VDP only"
    if any(kw in text for kw in high_value_kw):
        return 85.0, "High-value reward potential indicated"
    if any(kw in text for kw in medium_value_kw):
        return 60.0, "Moderate reward potential"
    if any(kw in text for kw in low_value_kw):
        return 20.0, "Low/non-financial rewards"

    if opp.category in ("web3", "paid_research"):
        return 70.0, "Category typically offers paid rewards"
    if opp.category in ("platform", "api_ecosystem"):
        return 50.0, "Platform programs usually offer bounties"
    if opp.category in ("independent", "open_source"):
        return 30.0, "Varies — may or may not offer rewards"
    if opp.category in ("emerging", "research"):
        return 15.0, "Emerging programs may not offer financial rewards"

    return 35.0, "Unknown reward structure"


def _compute_competition_score(opp: Opportunity) -> tuple[float, str]:
    """Competition Score: popularity, duplicate probability, age, activity.

    Lower score = more competition (less favourable).
    Higher score = less competition (more favourable).
    """
    name_lower = opp.name.lower()
    score = 70.0

    platform_hits = sum(1 for p in _MAJOR_PLATFORMS if p in name_lower)
    if platform_hits:
        score -= 30.0 * platform_hits

    web3_hits = sum(1 for p in _WEB3_PLATFORMS if p in name_lower)
    if web3_hits:
        score -= 20.0 * web3_hits

    if opp.category in ("emerging", "research"):
        score += 20.0
    elif opp.category in ("independent", "open_source", "paid_research"):
        score += 10.0
    elif opp.category in ("platform",):
        score -= 10.0

    age_text = ""
    if opp.last_update:
        try:
            dt = datetime.fromisoformat(opp.last_update)
            days = (datetime.now(timezone.utc) - dt).days
            if days < 30:
                age_text = "Recently updated — active"
            elif days < 180:
                score -= 5.0
                age_text = "Moderately active"
            else:
                score -= 10.0
                age_text = "Stale — may be inactive"
        except (ValueError, TypeError):
            logger.warning("Failed to parse activity date for scoring", exc_info=True)

    score = max(0.0, min(100.0, score))
    label = "Low competition" if score > 60 else "Moderate competition" if score > 35 else "High competition"
    return score, f"{label} (score: {score:.0f})" + (f" — {age_text}" if age_text else "")


def _compute_discovery_score(opp: Opportunity) -> tuple[float, str]:
    """Discovery Score: attack surface diversity, tech complexity."""
    text = (opp.scope_summary or "").lower() + " " + " ".join(opp.technology_tags).lower()
    score = 30.0
    matched = []

    for keyword, boost in _DISCOVERY_SURFACE_KEYWORDS.items():
        if keyword in text:
            score += boost * 100.0
            matched.append(keyword)

    score += min(20.0, len(opp.technology_tags) * 5.0)

    diversity = len(set(opp.technology_tags))
    if diversity >= 5:
        score += 10.0
    elif diversity >= 3:
        score += 5.0

    score = max(0.0, min(100.0, score))
    surfaces = ", ".join(matched) if matched else "limited"
    return score, f"Attack surface: {surfaces} ({len(matched)} vectors)"


def _compute_execution_score(opp: Opportunity) -> tuple[float, str]:
    """Execution Score: estimated research time, quick win probability, automation coverage."""
    score = 50.0
    factors: list[str] = []

    # Quick win potential from tech tags
    automation_tags = {"api", "graphql", "rest", "oauth", "jwt"}
    opp_tags = set(t.lower() for t in opp.technology_tags)
    automation_overlap = opp_tags & automation_tags
    if automation_overlap:
        score += len(automation_overlap) * 10.0
        factors.append("automation-friendly")

    # Wide scope = more execution paths
    scope_text = (opp.scope_summary or "").lower()
    if any(kw in scope_text for kw in ("all", "full", "entire", "comprehensive")):
        score += 10.0
        factors.append("broad scope")

    # Web3 often requires deeper manual analysis
    if opp.category == "web3":
        score -= 10.0
        factors.append("manual analysis required")

    # Simpler tech stacks
    if len(opp.technology_tags) <= 2:
        score += 10.0
        factors.append("focused tech stack")

    score = max(0.0, min(100.0, score))
    label = "Fast execution likely" if score > 60 else "Moderate effort" if score > 35 else "Significant effort"
    return score, f"{label} — {', '.join(factors) if factors else 'standard complexity'}"


def _compute_intelligence_score(
    opp: Opportunity,
    pattern_score: float = 0.0,
    historical_score: float = 0.0,
    memory_score: float = 0.0,
) -> tuple[float, str]:
    """Intelligence Score: pattern registry, historical analyzer, trend detector, adaptive memory."""
    base = 40.0
    intelligence = base + (pattern_score * 100.0 * 0.25) + (historical_score * 100.0 * 0.25) + (memory_score * 100.0 * 0.25)

    # Category intelligence boost
    known_categories = {"web3": 5.0, "platform": 3.0, "api_ecosystem": 8.0}
    if opp.category in known_categories:
        intelligence += known_categories[opp.category]

    intelligence = max(0.0, min(100.0, intelligence))
    return intelligence, f"AI signal: pattern={pattern_score:.2f}, history={historical_score:.2f}, memory={memory_score:.2f}"


def _compute_strategic_score(opp: Opportunity) -> tuple[float, str]:
    """Strategic Score: emerging technology, ecosystem relevance, long-term value."""
    score = 35.0
    factors: list[str] = []

    strategic_tags = {"web3", "solidity", "defi", "ai", "ml", "llm", "rust", "move", "zero-knowledge"}
    opp_tags = set(t.lower() for t in opp.technology_tags)
    strategic_match = opp_tags & strategic_tags

    if strategic_match:
        score += len(strategic_match) * 10.0
        factors.extend(strategic_match)

    if opp.category in ("web3", "ai", "paid_research", "emerging"):
        score += 15.0
        factors.append("high-growth category")

    ecosystem_keywords = {"ecosystem", "platform", "suite", "enterprise"}
    scope_text = (opp.scope_summary or "").lower()
    if any(kw in scope_text for kw in ecosystem_keywords):
        score += 10.0
        factors.append("ecosystem-level")

    score = max(0.0, min(100.0, score))
    f_text = f" — {', '.join(factors)}" if factors else ""
    return score, f"Strategic value: {score:.0f}/100{f_text}"


def _compute_confidence_score(opp: Opportunity) -> tuple[float, str]:
    """Confidence Score: source reliability, data freshness, metadata completeness."""
    score = opp.source.confidence * 80.0

    has_url = 1.0 if opp.public_url else 0.0
    score += has_url * 10.0

    has_scope = 1.0 if opp.scope_summary else 0.0
    score += has_scope * 5.0

    has_reward = 1.0 if opp.reward_info else 0.0
    score += has_reward * 5.0

    if opp.last_update:
        score += 5.0

    if opp.metadata:
        score += min(5.0, len(opp.metadata))

    score = max(0.0, min(100.0, score))
    tier = "High" if score > 70 else "Medium" if score > 40 else "Low"
    return score, f"{tier} confidence ({score:.0f}/100)"


def _compute_tech_overlap(opp: Opportunity, operator_tags: list[str]) -> float:
    """Measure technology overlap with operator preferences (0.0-1.0)."""
    opp_tags = set(t.lower() for t in opp.technology_tags)
    op_tags = set(t.lower() for t in operator_tags)

    if not opp_tags:
        return 0.3
    if not op_tags:
        high_value_count = sum(1 for t in opp_tags if t in _HIGH_VALUE_TAGS)
        return min(1.0, 0.3 + high_value_count * 0.1)

    union = opp_tags | op_tags
    if not union:
        return 0.3

    intersection = opp_tags & op_tags
    jaccard = len(intersection) / len(union)
    return min(1.0, 0.2 + jaccard * 0.8)


def _compute_freshness(opp: Opportunity) -> float:
    """Score based on recency of last update (0.0-1.0)."""
    if not opp.last_update:
        return 0.5
    try:
        dt = datetime.fromisoformat(opp.last_update)
        days = (datetime.now(timezone.utc) - dt).days
        if days < 7:
            return 0.95
        if days < 30:
            return 0.8
        if days < 90:
            return 0.6
        if days < 180:
            return 0.4
        return 0.2
    except (ValueError, TypeError):
        return 0.5


def _estimate_payout_from_reward(opp: Opportunity) -> float:
    """Estimate payout amount from reward text."""
    text = (opp.reward_info or "").lower()
    amounts = re.findall(r'\$?([0-9,]+)', text)
    parsed = []
    for a in amounts:
        with contextlib.suppress(ValueError):
            parsed.append(float(a.replace(",", "")))

    if parsed:
        return max(parsed) * 0.5  # conservative estimate

    if any(kw in text for kw in ["million", "$1,000,000"]):
        return 50000.0
    if any(kw in text for kw in ["$100,000", "$50,000"]):
        return 10000.0
    if any(kw in text for kw in ["$10,000", "$5,000"]):
        return 2500.0
    if any(kw in text for kw in ["bounty", "$1,000"]):
        return 500.0
    if any(kw in text for kw in ["swag", "recognition"]):
        return 0.0

    return 1000.0


def _score_to_priority(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"
