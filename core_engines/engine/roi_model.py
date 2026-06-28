"""
roi_model — Deterministic ROI engine for attack surface intelligence.

Computes ROI as a first-class decision signal that ranks hypotheses
by expected financial return, calibrated to real bug bounty economics.

Data flow:
  hypothesis + endpoint → payout_est × P(success) → expected_value
  → (expected_value - expected_cost) / expected_cost → ROI
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core_engines.engine.hypothesis.models import Hypothesis, HypothesisScore, VulnerabilityType

# ── Constants ────────────────────────────────────────────────────────

HOURLY_RATE = 50.0  # Standard bug bounty researcher hourly rate

# Base payout by vulnerability type (USD) — calibrated from HackerOne medians
BASE_PAYOUT: dict[VulnerabilityType, float] = {
    VulnerabilityType.IDOR: 3000.0,
    VulnerabilityType.AUTH_BYPASS: 5000.0,
    VulnerabilityType.SSRF: 4000.0,
    VulnerabilityType.XSS: 1500.0,
    VulnerabilityType.SQLI: 10000.0,
    VulnerabilityType.GRAPHQL_INTROSPECTION: 1000.0,
    VulnerabilityType.PRIVILEGE_ESCALATION: 6000.0,
    VulnerabilityType.DATA_EXPOSURE: 2500.0,
    VulnerabilityType.RATE_LIMIT_BYPASS: 500.0,
    VulnerabilityType.WEB3_SIGNATURE_REPLAY: 8000.0,
    VulnerabilityType.WEB3_RPC_LEAK: 2000.0,
    VulnerabilityType.BUSINESS_LOGIC: 2000.0,
    VulnerabilityType.FILE_OPERATION: 3000.0,
    VulnerabilityType.SSTI: 5000.0,
}

# Estimated research hours to validate by type
BASE_HOURS: dict[VulnerabilityType, float] = {
    VulnerabilityType.IDOR: 3.0,
    VulnerabilityType.AUTH_BYPASS: 6.0,
    VulnerabilityType.SSRF: 8.0,
    VulnerabilityType.XSS: 3.0,
    VulnerabilityType.SQLI: 12.0,
    VulnerabilityType.GRAPHQL_INTROSPECTION: 2.0,
    VulnerabilityType.PRIVILEGE_ESCALATION: 8.0,
    VulnerabilityType.DATA_EXPOSURE: 4.0,
    VulnerabilityType.RATE_LIMIT_BYPASS: 2.0,
    VulnerabilityType.WEB3_SIGNATURE_REPLAY: 10.0,
    VulnerabilityType.WEB3_RPC_LEAK: 6.0,
    VulnerabilityType.BUSINESS_LOGIC: 5.0,
    VulnerabilityType.FILE_OPERATION: 5.0,
    VulnerabilityType.SSTI: 8.0,
}

# Payout multipliers for high-value signal keywords
SIGNAL_PAYOUT_MULTIPLIERS: dict[str, float] = {
    "billing": 1.5,
    "admin": 1.3,
    "export": 1.2,
    "internal": 1.25,
    "identity": 1.15,
    "multi_tenant": 1.4,
    "graphql": 1.1,
    "web3": 1.6,
    "ownership_risk": 1.2,
}

# Time multipliers for complex paths
COMPLEXITY_HOURS_MULTIPLIERS: dict[str, float] = {
    "uuid": 1.3,
    "mutating_method": 1.4,
    "auth": 1.5,
    "file_operation": 1.2,
    "sensitive_operation": 1.1,
}


@dataclass(frozen=True)
class ROIScore:
    """Immutable ROI computation result."""

    expected_return: float
    expected_cost: float
    roi_ratio: float
    roi_normalized: float
    payout_estimate: float
    time_cost_hours: float
    probability_success: float
    breakdown: dict[str, float] = field(default_factory=dict)

    @property
    def is_profitable(self) -> bool:
        return self.roi_ratio > 0.0


class PayoutEstimator:
    """Estimates bug bounty payout based on vulnerability type and endpoint signals."""

    @staticmethod
    def estimate(hypothesis: Hypothesis) -> float:
        vt = hypothesis.vulnerability_type
        base = BASE_PAYOUT.get(vt, 2000.0)

        signals = hypothesis.endpoint.get("signals", [])
        multiplier = 1.0
        for signal, mult in SIGNAL_PAYOUT_MULTIPLIERS.items():
            if signal in signals:
                multiplier *= mult

        labels = hypothesis.endpoint.get("labels", [])
        for label, mult in SIGNAL_PAYOUT_MULTIPLIERS.items():
            if label in labels:
                multiplier *= mult

        return round(base * multiplier, 2)

    @staticmethod
    def estimate_hours(hypothesis: Hypothesis) -> float:
        vt = hypothesis.vulnerability_type
        base = BASE_HOURS.get(vt, 5.0)

        signals = hypothesis.endpoint.get("signals", [])
        multiplier = 1.0
        for signal, mult in COMPLEXITY_HOURS_MULTIPLIERS.items():
            if signal in signals:
                multiplier *= mult

        # Graph hypotheses (no single endpoint) get 150% time
        if not hypothesis.endpoint.get("id"):
            multiplier *= 1.5

        return round(base * multiplier, 1)


def calculate_roi(
    hypothesis: Hypothesis,
) -> ROIScore:
    """
    Compute ROI for a hypothesis using real bounty economics.

    Formula:
      P(success) = L * E * C
      expected_return = P(success) * payout_estimate
      expected_cost = hours * HOURLY_RATE
      roi_ratio = (expected_return - expected_cost) / expected_cost
      roi_normalized = clamp(roi_ratio * 10 + 50, 0, 100)
    """
    payout = PayoutEstimator.estimate(hypothesis)
    hours = PayoutEstimator.estimate_hours(hypothesis)

    likelihood = hypothesis.likelihood
    exploitability = hypothesis.exploitability
    confidence = hypothesis.confidence

    p_success = likelihood * exploitability * confidence
    # Floor at realistic minimum: even low-confidence hypotheses have small success chance
    p_success = max(p_success, 0.001)

    expected_return = p_success * payout
    expected_cost = hours * HOURLY_RATE

    roi_ratio = 0.0 if expected_cost <= 0 else (expected_return - expected_cost) / expected_cost

    # Normalize: roi_ratio -5..+5 maps to 0..100, centered at 50 (break-even)
    roi_normalized = max(0.0, min(100.0, roi_ratio * 10.0 + 50.0))

    return ROIScore(
        expected_return=round(expected_return, 2),
        expected_cost=round(expected_cost, 2),
        roi_ratio=round(roi_ratio, 4),
        roi_normalized=round(roi_normalized, 2),
        payout_estimate=round(payout, 2),
        time_cost_hours=round(hours, 1),
        probability_success=round(p_success, 4),
        breakdown={
            "payout_estimate": round(payout, 2),
            "time_cost_hours": round(hours, 1),
            "hourly_rate": HOURLY_RATE,
            "likelihood": likelihood,
            "exploitability": exploitability,
            "confidence": confidence,
            "probability_success": round(p_success, 4),
            "expected_return": round(expected_return, 2),
            "expected_cost": round(expected_cost, 2),
            "roi_ratio": round(roi_ratio, 4),
            "payout_multiplier": round(payout / BASE_PAYOUT.get(hypothesis.vulnerability_type, 2000.0), 2),
        },
    )


def update_roi_after_verdict(
    original_roi: ROIScore,
    actual_payout: float,
    actual_hours: float,
    verdict_status: str,
    validation_confidence: float,
) -> ROIScore:
    """
    Update ROI after a validation verdict is returned.

    This creates the learning signal — predicted vs realized ROI.
    """
    actual_cost = actual_hours * HOURLY_RATE
    realized_return = actual_payout if verdict_status == "confirmed" else 0.0

    realized_ratio = 0.0 if actual_cost <= 0 else (realized_return - actual_cost) / actual_cost

    realized_normalized = max(0.0, min(100.0, realized_ratio * 10.0 + 50.0))

    p_success_actual = 1.0 if verdict_status == "confirmed" else 0.0

    prediction_error = abs(original_roi.probability_success - p_success_actual)

    return ROIScore(
        expected_return=round(realized_return, 2),
        expected_cost=round(actual_cost, 2),
        roi_ratio=round(realized_ratio, 4),
        roi_normalized=round(realized_normalized, 2),
        payout_estimate=round(actual_payout, 2),
        time_cost_hours=round(actual_hours, 1),
        probability_success=round(p_success_actual, 4),
        breakdown={
            "predicted_return": original_roi.expected_return,
            "predicted_cost": original_roi.expected_cost,
            "predicted_roi_ratio": original_roi.roi_ratio,
            "predicted_probability": original_roi.probability_success,
            "realized_return": round(realized_return, 2),
            "realized_cost": round(actual_cost, 2),
            "realized_roi_ratio": round(realized_ratio, 4),
            "prediction_error": round(prediction_error, 4),
            "verdict_status": 1.0 if verdict_status == "confirmed" else 0.0,
            "validation_confidence": validation_confidence,
        },
    )


def normalize_roi_scores(
    hypotheses: list[Hypothesis],
    min_roi: float = 0.0,
    max_roi: float = 100.0,
) -> list[Hypothesis]:
    """
    Normalize ROI scores across a set of hypotheses.
    Ensures efficient frontier — the best hypothesis always gets 100, worst gets 0.
    """
    if not hypotheses:
        return hypotheses

    roi_values = [h.roi_score for h in hypotheses]
    lo = min(roi_values)
    hi = max(roi_values)
    span = hi - lo

    if span < 1e-6:
        return hypotheses

    normalized = []
    for h in hypotheses:
        raw = h.roi_score
        norm = min_roi + (raw - lo) / span * (max_roi - min_roi)

        breakdown = dict(h.score.breakdown) if hasattr(h.score, "breakdown") else {}
        breakdown["roi_raw"] = raw
        breakdown["roi_normalized"] = round(norm, 2)

        new_score = HypothesisScore(
            likelihood=h.score.likelihood,
            impact=h.score.impact,
            exploitability=h.score.exploitability,
            confidence=h.score.confidence,
            priority_score=h.score.priority_score,
            breakdown=breakdown,
        )

        normalized.append(Hypothesis(
            id=h.id,
            vulnerability_type=h.vulnerability_type,
            target_id=h.target_id,
            target_name=h.target_name,
            endpoint=h.endpoint,
            likelihood=h.likelihood,
            impact=h.impact,
            exploitability=h.exploitability,
            confidence=h.confidence,
            priority_score=h.priority_score,
            roi_score=round(norm, 2),
            evidence=h.evidence,
            reasoning=h.reasoning,
            suggested_actions=h.suggested_actions,
            source=h.source,
            vector=h.vector,
            attack_surface_labels=h.attack_surface_labels,
            similarity_to_past=h.similarity_to_past,
            past_pattern_id=h.past_pattern_id,
            score=new_score,
        ))

    return normalized


def apply_roi_to_priority(
    priority_score: float,
    roi_normalized: float,
    roi_weight: float = 0.3,
) -> float:
    """
    Blend existing priority score with ROI to produce a combined ranking score.

    composite = priority_score * (1 - roi_weight) + (roi_normalized / 10) * roi_weight

    This ensures ROI is a modifier, not a replacement — high-risk hypotheses
    still rank well, but those with strong financial return get a boost.
    """
    roi_factor = roi_normalized / 10.0  # 0..10 range
    return round(priority_score * (1.0 - roi_weight) + roi_factor * roi_weight, 2)


__all__ = [
    "ROIScore",
    "PayoutEstimator",
    "calculate_roi",
    "update_roi_after_verdict",
    "normalize_roi_scores",
    "apply_roi_to_priority",
]
