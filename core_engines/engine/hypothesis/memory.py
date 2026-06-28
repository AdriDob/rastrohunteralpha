"""
hypothesis.memory — Memory-backed hypothesis refinement.

Uses past confirmed findings from MemoryPatternLibrary to:
- Boost or penalize hypothesis scores based on historical success
- Attach similar past pattern IDs for traceability
- Compute per-vulnerability-type success rates
"""

from __future__ import annotations

import logging
from typing import Any

LOG = logging.getLogger("rastro.hypothesis.memory")

from core_engines.engine.hypothesis.models import Hypothesis, VulnerabilityType
from core_engines.memory.memory import MemoryPatternLibrary
from core_engines.memory.pattern_extractor import PatternExtractor


class HypothesisMemory:
    def __init__(self, memory: MemoryPatternLibrary | None = None):
        self.memory = memory or MemoryPatternLibrary()
        self.pattern_extractor = PatternExtractor()
        self._success_cache: dict[str, float] = {}

    def compute_success_rate(self, vt: VulnerabilityType) -> float:
        key = vt.value
        if key in self._success_cache:
            return self._success_cache[key]
        try:
            rate = self.memory.get_success_rate(str(vt.value))
        except Exception:
            rate = 0.0
        self._success_cache[key] = rate
        return rate

    def compute_all_success_rates(self) -> dict[str, float]:
        rates = {}
        for vt in VulnerabilityType:
            rates[vt.value] = self.compute_success_rate(vt)
        return rates

    def find_similar_pattern(
        self, h: Hypothesis, threshold: float = 0.4,
    ) -> dict[str, Any] | None:
        path = str(h.endpoint.get("path", ""))
        labels = h.endpoint.get("labels", [])
        signals = h.endpoint.get("signals", [])
        try:
            patterns = self.memory.find_similar_endpoints(path, list(set(labels + signals)))
            if patterns:
                best = patterns[0]
                if isinstance(best, dict) and best.get("similarity", 0) >= threshold:
                    return best
        except Exception:
            LOG.warning("Failed to find similar endpoints in memory", exc_info=True)
        return None

    def refine(
        self, hypotheses: list[Hypothesis],
    ) -> list[Hypothesis]:
        refined = []
        success_rates = self.compute_all_success_rates()

        for h in hypotheses:
            past_success = success_rates.get(h.vulnerability_type.value, 0.0)
            pattern = self.find_similar_pattern(h)
            similarity = float(pattern.get("similarity", 0.0)) if pattern else 0.0
            pattern_id = str(pattern.get("id", "")) if pattern else None

            likelihood_boost = 0.0
            confidence_boost = 0.0

            if past_success >= 0.6:
                likelihood_boost = 0.10
                confidence_boost = 0.10
            elif past_success >= 0.3:
                likelihood_boost = 0.05
                confidence_boost = 0.05
            elif past_success <= 0.05:
                likelihood_boost = -0.05
                confidence_boost = -0.05

            if similarity >= 0.6:
                likelihood_boost += 0.08
                confidence_boost += 0.08
            elif similarity >= 0.3:
                likelihood_boost += 0.03
                confidence_boost += 0.03

            refined_h = Hypothesis(
                id=h.id,
                vulnerability_type=h.vulnerability_type,
                target_id=h.target_id,
                target_name=h.target_name,
                endpoint=h.endpoint,
                likelihood=min(max(h.likelihood + likelihood_boost, 0.05), 0.95),
                impact=h.impact,
                exploitability=h.exploitability,
                confidence=min(max(h.confidence + confidence_boost, 0.05), 0.95),
                priority_score=0.0,
                evidence=h.evidence,
                reasoning=h.reasoning,
                suggested_actions=h.suggested_actions,
                source=h.source,
                vector=h.vector,
                attack_surface_labels=h.attack_surface_labels,
                similarity_to_past=similarity,
                past_pattern_id=pattern_id,
            )
            refined.append(refined_h)

        return refined
