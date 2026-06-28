from dataclasses import dataclass
from typing import Any

from core_engines.validation.replayer import ComparisonResult
from core_engines.validation.rules import ValidationReport

WEIGHTS = {
    "consistency": 0.40,
    "signal": 0.30,
    "evidence_strength": 0.20,
    "noise_penalty": -0.10,
}


@dataclass
class ConfidenceScore:
    score: float
    breakdown: dict[str, float]
    level: str


class ConfidenceScorer:
    def calculate(
        self,
        results: list[ComparisonResult],
        validation: ValidationReport,
        endpoint_signals: dict[str, Any],
    ) -> ConfidenceScore:
        total = len(results)
        if total == 0:
            return ConfidenceScore(
                score=0.0,
                breakdown={
                    "consistency_score": 0.0,
                    "signal_score": 0.0,
                    "evidence_strength": 0.0,
                    "noise_penalty": 0.0,
                },
                level="none",
            )

        consistent_count = sum(1 for r in results if r.consistent)
        consistency_score = consistent_count / total

        risk_score = float(endpoint_signals.get("risk_score", 0))
        signal_score = min(risk_score / 100.0, 1.0)

        total_rules = 4
        passed_rules = len(validation.passed_rules)
        evidence_strength = passed_rules / total_rules

        noise_count = sum(1 for r in results if r.has_rate_limit or r.has_timeout)
        noise_penalty = noise_count / total

        raw_score = (
            (consistency_score * WEIGHTS["consistency"])
            + (signal_score * WEIGHTS["signal"])
            + (evidence_strength * WEIGHTS["evidence_strength"])
            + (noise_penalty * WEIGHTS["noise_penalty"])
        )
        score = max(0.0, min(1.0, round(raw_score, 4)))

        if score >= 0.8:
            level = "high"
        elif score >= 0.6:
            level = "medium"
        elif score >= 0.3:
            level = "low"
        else:
            level = "none"

        return ConfidenceScore(
            score=score,
            breakdown={
                "consistency_score": round(consistency_score, 4),
                "signal_score": round(signal_score, 4),
                "evidence_strength": round(evidence_strength, 4),
                "noise_penalty": round(noise_penalty, 4),
            },
            level=level,
        )
