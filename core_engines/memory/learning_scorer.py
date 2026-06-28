"""
Learning scorer: adjust endpoint scoring based on historical pattern library.

Boosts confidence for patterns seen before, estimates payouts based on history.
"""
from typing import Any


class ConfidenceBooster:
    """Boost endpoint confidence based on pattern library history."""

    # Confidence boost thresholds
    MAX_BOOST = 0.15
    WAF_PENALTY = -0.10

    @staticmethod
    def boost_confidence(
        base_confidence: float,
        endpoint_path: str,
        entity_type: str | None,
        similar_patterns: list[dict[str, Any]],
        waf_detected: bool = False,
    ) -> float:
        """
        Boost confidence score based on similar patterns in library.

        Args:
            base_confidence: Original confidence score (0-1)
            endpoint_path: Endpoint path
            entity_type: Detected entity type
            similar_patterns: Similar patterns from library (with similarity_score)
            waf_detected: If WAF was detected in similar patterns

        Returns: Boosted confidence score (capped at 1.0, min 0.0)
        """
        boosted = base_confidence

        if not similar_patterns:
            return max(0.0, min(1.0, boosted))

        # Boost by best match similarity
        best_match = similar_patterns[0]
        similarity_score = best_match.get("similarity_score", 0)

        # Normalize similarity score to boost factor
        if similarity_score >= 6:
            boost_factor = 0.15
        elif similarity_score >= 4:
            boost_factor = 0.10
        elif similarity_score >= 2:
            boost_factor = 0.05
        else:
            boost_factor = 0.0

        boosted += boost_factor

        # WAF penalty if detected in similar endpoints
        if waf_detected:
            boosted += ConfidenceBooster.WAF_PENALTY

        # Cap to [0, 1]
        return max(0.0, min(1.0, boosted))

    @staticmethod
    def boost_by_entity_history(
        base_confidence: float,
        entity_type: str,
        entity_vuln_stats: dict[str, Any],
    ) -> float:
        """
        Boost confidence based on entity type history.

        If this entity type has been vulnerable before, boost confidence.
        """
        if not entity_vuln_stats or entity_type not in entity_vuln_stats:
            return base_confidence

        stats = entity_vuln_stats[entity_type]
        total_seen = stats.get("total_tested", 1)
        confirmed = stats.get("confirmed_count", 0)

        success_rate = confirmed / total_seen if total_seen > 0 else 0.0

        # If entity type has high success rate, boost more
        if success_rate >= 0.8:
            boost = 0.15
        elif success_rate >= 0.5:
            boost = 0.10
        elif success_rate >= 0.3:
            boost = 0.05
        else:
            boost = 0.0

        boosted = base_confidence + boost
        return max(0.0, min(1.0, boosted))


class PayoutEstimator:
    """Estimate payout based on finding type and historical data."""

    # Base payouts by vulnerability type
    BASE_PAYOUTS = {
        "idor": 500,
        "auth_bypass": 1000,
        "data_exposure": 750,
        "privilege_escalation": 600,
        "unknown": 300,
    }

    # Multipliers by severity
    SEVERITY_MULTIPLIERS = {
        "critical": 3.0,
        "high": 2.0,
        "medium": 1.0,
        "low": 0.5,
    }

    # Entity type multipliers (more sensitive entities = higher payout)
    ENTITY_MULTIPLIERS = {
        "user": 1.2,
        "organization": 1.5,
        "billing": 2.0,
        "admin": 1.8,
        "file": 1.3,
        "data": 1.0,
        "unknown": 0.8,
    }

    @staticmethod
    def estimate_payout(
        vuln_type: str,
        severity: str,
        entity_type: str | None,
        historical_payouts: list[float],
    ) -> float:
        """
        Estimate payout for finding.

        Args:
            vuln_type: Type of vulnerability
            severity: Severity level
            entity_type: Entity type affected
            historical_payouts: List of payouts for similar findings

        Returns: Estimated payout in USD
        """
        base = PayoutEstimator.BASE_PAYOUTS.get(vuln_type, 300)
        severity_mult = PayoutEstimator.SEVERITY_MULTIPLIERS.get(severity, 1.0)
        entity_mult = PayoutEstimator.ENTITY_MULTIPLIERS.get(entity_type or "unknown", 0.8)

        calculated = base * severity_mult * entity_mult

        # If we have historical data, average with calculation
        if historical_payouts:
            avg_historical = sum(historical_payouts) / len(historical_payouts)
            # Weight: 60% calculated, 40% historical
            estimated = (0.6 * calculated) + (0.4 * avg_historical)
        else:
            estimated = calculated

        return round(estimated, 2)

    @staticmethod
    def estimate_by_confidence(
        base_payout: float,
        confidence: float,
    ) -> float:
        """
        Adjust payout estimate by confidence score.

        Higher confidence = more likely to be accepted = slightly higher estimate.
        """
        if confidence >= 0.8:
            multiplier = 1.2
        elif confidence >= 0.7:
            multiplier = 1.1
        elif confidence >= 0.6:
            multiplier = 1.0
        else:
            multiplier = 0.8

        return round(base_payout * multiplier, 2)


class LearningScorer:
    """Unified learning scorer combining confidence boost + payout estimation."""

    def __init__(
        self,
        confidence_booster: ConfidenceBooster | None = None,
        payout_estimator: PayoutEstimator | None = None,
    ):
        self._booster = confidence_booster or ConfidenceBooster()
        self._estimator = payout_estimator or PayoutEstimator()

    def score_endpoint_with_learning(
        self,
        base_confidence: float,
        endpoint_path: str,
        entity_type: str | None,
        vuln_type: str,
        severity: str,
        similar_patterns: list[dict[str, Any]],
        entity_vuln_stats: dict[str, Any] | None = None,
        historical_payouts: list[float] | None = None,
        waf_detected: bool = False,
    ) -> dict[str, Any]:
        """
        Score endpoint with full learning applied.

        Returns dict with boosted confidence, payout estimate, and reasoning.
        """
        # Boost confidence
        boosted_confidence = self._booster.boost_confidence(
            base_confidence=base_confidence,
            endpoint_path=endpoint_path,
            entity_type=entity_type,
            similar_patterns=similar_patterns,
            waf_detected=waf_detected,
        )

        if entity_vuln_stats:
            boosted_confidence = self._booster.boost_by_entity_history(
                boosted_confidence,
                entity_type or "unknown",
                entity_vuln_stats,
            )

        # Estimate payout
        base_payout = self._estimator.estimate_payout(
            vuln_type=vuln_type,
            severity=severity,
            entity_type=entity_type,
            historical_payouts=historical_payouts or [],
        )

        final_payout = self._estimator.estimate_by_confidence(
            base_payout,
            boosted_confidence,
        )

        # Build reasoning
        reasoning = []
        if similar_patterns:
            reasoning.append(
                f"Pattern known ({len(similar_patterns)} similar found, "
                f"best match score={similar_patterns[0].get('similarity_score', 0)})"
            )
        if waf_detected:
            reasoning.append("WAF detected in similar endpoints (penalty applied)")
        if entity_vuln_stats and entity_type in entity_vuln_stats:
            stats = entity_vuln_stats[entity_type]
            confirmed = stats.get("confirmed_count", 0)
            reasoning.append(f"Entity '{entity_type}' has {confirmed} confirmed findings")

        return {
            "base_confidence": base_confidence,
            "boosted_confidence": boosted_confidence,
            "confidence_boost_factor": boosted_confidence - base_confidence,
            "base_payout": base_payout,
            "final_payout_estimate": final_payout,
            "reasoning": reasoning,
        }
