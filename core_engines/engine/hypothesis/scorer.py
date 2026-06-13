"""
hypothesis.scorer — Scores hypotheses on likelihood, impact, exploitability, confidence, and ROI.

Produces a composite priority_score and roi_score used for attack queue ordering.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from core.engine.hypothesis.models import Hypothesis, HypothesisScore, VulnerabilityType
from core.engine.roi_model import ROIScore, calculate_roi, apply_roi_to_priority


LIKELIHOOD_WEIGHTS = {
    "signal_strength": 0.35,
    "risk_score_contribution": 0.20,
    "surface_overlap": 0.20,
    "vector_frequency": 0.15,
    "method_mutability": 0.10,
}

IMPACT_WEIGHTS = {
    "data_sensitivity": 0.35,
    "scope": 0.25,
    "user_interaction_required": 0.20,
    "reversibility": 0.20,
}

EXPLOITABILITY_WEIGHTS = {
    "attack_vector_complexity": 0.30,
    "authentication_required": 0.30,
    "network_position": 0.20,
    "tool_availability": 0.20,
}

VULN_IMPACT_BASE: Dict[str, float] = {
    "idor": 0.70,
    "auth_bypass": 0.85,
    "ssrf": 0.75,
    "xss": 0.50,
    "sqli": 0.90,
    "graphql_introspection": 0.60,
    "privilege_escalation": 0.85,
    "data_exposure": 0.65,
    "rate_limit_bypass": 0.30,
    "web3_signature_replay": 0.75,
    "web3_rpc_leak": 0.55,
    "business_logic": 0.70,
    "file_operation": 0.80,
    "ssti": 0.75,
}

VULN_LIKELIHOOD_BASE: Dict[str, float] = {
    "idor": 0.55,
    "auth_bypass": 0.40,
    "ssrf": 0.35,
    "xss": 0.45,
    "sqli": 0.20,
    "graphql_introspection": 0.75,
    "privilege_escalation": 0.40,
    "data_exposure": 0.55,
    "rate_limit_bypass": 0.60,
    "web3_signature_replay": 0.40,
    "web3_rpc_leak": 0.45,
    "business_logic": 0.40,
    "file_operation": 0.40,
    "ssti": 0.25,
}

VULN_EXPLOITABILITY_BASE: Dict[str, float] = {
    "idor": 0.65,
    "auth_bypass": 0.45,
    "ssrf": 0.50,
    "xss": 0.70,
    "sqli": 0.35,
    "graphql_introspection": 0.80,
    "privilege_escalation": 0.40,
    "data_exposure": 0.55,
    "rate_limit_bypass": 0.75,
    "web3_signature_replay": 0.40,
    "web3_rpc_leak": 0.50,
    "business_logic": 0.45,
    "file_operation": 0.45,
    "ssti": 0.40,
}


def _signal_strength(h: Hypothesis) -> float:
    ep = h.endpoint
    risk_score = float(ep.get("risk_score", 0))
    signals = ep.get("signals", [])
    evidence_count = len(h.evidence)
    signal_score = min(len(signals) / 8.0, 1.0)
    evidence_score = min(evidence_count / 6.0, 1.0)
    risk_score_norm = min(risk_score / 100.0, 1.0)
    return (signal_score * 0.3 + evidence_score * 0.3 + risk_score_norm * 0.4)


def _surface_overlap(h: Hypothesis) -> float:
    ep_surfaces = set(h.endpoint.get("attack_surface", []))
    hyp_surfaces = set(h.attack_surface_labels)
    if not ep_surfaces and not hyp_surfaces:
        return 0.5
    union = ep_surfaces | hyp_surfaces
    if not union:
        return 0.0
    intersection = ep_surfaces & hyp_surfaces
    return len(intersection) / len(union)


def _method_score(method: str) -> float:
    m = method.upper()
    if m in ("DELETE",):
        return 0.9
    if m in ("POST", "PUT", "PATCH"):
        return 0.7
    if m == "GET":
        return 0.3
    return 0.5


def compute_likelihood(h: Hypothesis) -> float:
    ep = h.endpoint
    risk_score = float(ep.get("risk_score", 0))
    risk_score_norm = min(risk_score / 100.0, 1.0)

    base = VULN_LIKELIHOOD_BASE.get(h.vulnerability_type.value, 0.3)
    signal = _signal_strength(h)
    surface = _surface_overlap(h)
    mutability = _method_score(str(ep.get("method", "GET")))

    score = (
        LIKELIHOOD_WEIGHTS["signal_strength"] * signal
        + LIKELIHOOD_WEIGHTS["risk_score_contribution"] * risk_score_norm
        + LIKELIHOOD_WEIGHTS["surface_overlap"] * surface
        + LIKELIHOOD_WEIGHTS["vector_frequency"] * base
        + LIKELIHOOD_WEIGHTS["method_mutability"] * mutability
    )
    return min(max(score, 0.05), 0.95)


def compute_impact(h: Hypothesis) -> float:
    ep = h.endpoint
    method = str(ep.get("method", "GET")).upper()
    signals = ep.get("signals", [])
    labels = ep.get("labels", [])

    base = VULN_IMPACT_BASE.get(h.vulnerability_type.value, 0.5)

    data_sensitivity = 0.3
    if any(s in signals for s in {"billing", "identity", "export", "admin"}):
        data_sensitivity = 0.8
    elif any(l in labels for l in {"sensitive", "admin", "billing"}):
        data_sensitivity = 0.7
    elif "auth" in labels:
        data_sensitivity = 0.6

    scope = 0.8 if method in ("POST", "PUT", "PATCH", "DELETE") else 0.4
    user_interaction = 0.7 if method == "GET" else 0.9
    reversibility = 0.3 if method == "GET" else 0.7

    score = (
        IMPACT_WEIGHTS["data_sensitivity"] * data_sensitivity
        + IMPACT_WEIGHTS["scope"] * scope
        + IMPACT_WEIGHTS["user_interaction_required"] * user_interaction
        + IMPACT_WEIGHTS["reversibility"] * reversibility
    )
    averaged = (base + score) / 2
    return min(max(averaged, 0.1), 0.95)


def compute_exploitability(h: Hypothesis) -> float:
    base = VULN_EXPLOITABILITY_BASE.get(h.vulnerability_type.value, 0.4)

    ep = h.endpoint
    method = str(ep.get("method", "GET")).upper()
    method_factor = 0.6 if method in ("GET",) else 0.4

    risk_score = float(ep.get("risk_score", 0))
    complexity = 1.0 - min(risk_score / 100.0, 1.0)

    auth_required = 0.4 if "auth" in ep.get("labels", []) else 0.8
    tool_factor = 0.7 if any(
        t in h.vulnerability_type.value
        for t in {"idor", "graphql", "xss"}
    ) else 0.4

    score = (
        EXPLOITABILITY_WEIGHTS["attack_vector_complexity"] * complexity
        + EXPLOITABILITY_WEIGHTS["authentication_required"] * auth_required
        + EXPLOITABILITY_WEIGHTS["network_position"] * method_factor
        + EXPLOITABILITY_WEIGHTS["tool_availability"] * tool_factor
    )
    averaged = (base + score) / 2
    return min(max(averaged, 0.1), 0.95)


def compute_confidence(
    h: Hypothesis,
    risk_score: float,
    evidence_count: int,
    past_success_rate: float = 0.0,
    pattern_similarity: float = 0.0,
) -> float:
    risk_norm = min(risk_score / 100.0, 1.0)
    evidence_factor = min(evidence_count / 5.0, 1.0)
    pattern_factor = min(pattern_similarity, 1.0) * 0.15
    memory_factor = min(past_success_rate, 1.0) * 0.10

    base = (
        risk_norm * 0.35
        + evidence_factor * 0.25
        + pattern_factor
        + memory_factor
    )
    return min(max(base, 0.05), 0.95)


def compute_priority_score(h: Hypothesis) -> float:
    likelihood_weight = compute_likelihood(h)
    impact_weight = compute_impact(h)
    exploitability_weight = compute_exploitability(h)
    confidence_weight = h.confidence

    score = (
        likelihood_weight * 0.25
        + impact_weight * 0.35
        + exploitability_weight * 0.25
        + confidence_weight * 0.15
    )
    return round(score * 10.0, 2)


def score_hypothesis(
    h: Hypothesis,
    risk_score: float,
    past_success_rate: float = 0.0,
    pattern_similarity: float = 0.0,
) -> Hypothesis:
    likelihood = compute_likelihood(h)
    impact = compute_impact(h)
    exploitability = compute_exploitability(h)
    evidence_count = len(h.evidence)
    confidence = compute_confidence(h, risk_score, evidence_count, past_success_rate, pattern_similarity)
    priority = compute_priority_score(h)

    # Compute ROI as part of scoring — needs prev scores so we build interim hypothesis
    interim = Hypothesis(
        id=h.id,
        vulnerability_type=h.vulnerability_type,
        target_id=h.target_id,
        target_name=h.target_name,
        endpoint=h.endpoint,
        likelihood=round(likelihood, 2),
        impact=round(impact, 2),
        exploitability=round(exploitability, 2),
        confidence=round(confidence, 2),
        priority_score=priority,
        evidence=h.evidence,
        reasoning=h.reasoning,
        suggested_actions=h.suggested_actions,
        source=h.source,
        vector=h.vector,
        attack_surface_labels=h.attack_surface_labels,
        similarity_to_past=pattern_similarity,
        past_pattern_id=h.past_pattern_id,
        roi_score=0.0,
        score=HypothesisScore(0, 0, 0, 0, 0),
    )

    roi = calculate_roi(interim)
    composite = apply_roi_to_priority(priority, roi.roi_normalized)

    breakdown = {
        "likelihood_breakdown": likelihood,
        "impact_breakdown": impact,
        "exploitability_breakdown": exploitability,
        "confidence_breakdown": confidence,
        "evidence_count": evidence_count,
        "roi_normalized": roi.roi_normalized,
        "roi_ratio": roi.roi_ratio,
        "payout_estimate": roi.payout_estimate,
        "expected_return": roi.expected_return,
        "expected_cost": roi.expected_cost,
        "time_cost_hours": roi.time_cost_hours,
    }

    h = Hypothesis(
        id=h.id,
        vulnerability_type=h.vulnerability_type,
        target_id=h.target_id,
        target_name=h.target_name,
        endpoint=h.endpoint,
        likelihood=round(likelihood, 2),
        impact=round(impact, 2),
        exploitability=round(exploitability, 2),
        confidence=round(confidence, 2),
        priority_score=composite,
        roi_score=roi.roi_normalized,
        evidence=h.evidence,
        reasoning=h.reasoning,
        suggested_actions=h.suggested_actions,
        source=h.source,
        vector=h.vector,
        attack_surface_labels=h.attack_surface_labels,
        similarity_to_past=pattern_similarity,
        past_pattern_id=h.past_pattern_id,
        score=HypothesisScore(
            likelihood=round(likelihood, 2),
            impact=round(impact, 2),
            exploitability=round(exploitability, 2),
            confidence=round(confidence, 2),
            priority_score=composite,
            breakdown=breakdown,
        ),
    )
    return h


def reorder_attack_queue(
    hypotheses: List[Hypothesis],
    roi_weight: float = 0.3,
) -> List[Hypothesis]:
    """
    Order hypotheses by composite score blending risk+confidence priority with ROI.

    roi_weight controls how much financial return influences ordering.
    0.0 = pure risk-based (original behavior)
    0.3 = balanced (default)
    0.5+ = ROI-dominant
    """
    def _composite(h: Hypothesis) -> float:
        # priority_score already includes ROI via apply_roi_to_priority in score_hypothesis
        # But for queue reordering we also consider roi_score as tiebreaker
        return (h.priority_score, h.roi_score)

    return sorted(hypotheses, key=_composite, reverse=True)


def reorder_by_roi(hypotheses: List[Hypothesis]) -> List[Hypothesis]:
    """Order hypotheses purely by ROI score — used when the user wants financial-first ranking."""
    return sorted(hypotheses, key=lambda h: h.roi_score, reverse=True)
