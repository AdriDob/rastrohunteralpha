"""
intelligence.engine — System Intelligence Engine.

Correlación global entre targets, detección de tendencias de
vulnerabilidades y patrones cross-program.

Alimenta el AI Assistant con datos consolidados.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core_engines.ai.assistant import ScanAssistant

LOG = logging.getLogger("rastro.intelligence")


@dataclass
class TrendingVulnerability:
    vulnerability_type: str
    count: int
    targets_affected: List[str]
    avg_risk_score: float = 0.0
    trend_direction: str = "stable"  # rising, falling, stable


@dataclass
class CrossTargetPattern:
    pattern: str
    targets: List[str]
    endpoint_count: int
    avg_risk: float = 0.0


@dataclass
class IntelligenceReport:
    total_targets: int = 0
    total_endpoints: int = 0
    total_hypotheses: int = 0
    total_verified: int = 0
    total_reported: int = 0
    estimated_total_value: float = 0.0
    avg_roi_score: float = 0.0
    trending_vulnerabilities: List[TrendingVulnerability] = field(default_factory=list)
    cross_target_patterns: List[CrossTargetPattern] = field(default_factory=list)
    top_recommendation: str = ""
    summary: str = ""


class SystemIntelligenceEngine:
    """Correlación global y generación de inteligencia actionable."""

    def __init__(self):
        self._assistant = ScanAssistant()

    def analyze_targets(
        self,
        targets_data: Dict[str, List[Dict[str, Any]]],
        hypotheses_by_target: Optional[Dict[int, List[Any]]] = None,
        verdicts_by_target: Optional[Dict[int, List[Dict[str, Any]]]] = None,
    ) -> IntelligenceReport:
        """Analiza datos globales y genera un reporte de inteligencia."""
        all_endpoints: List[Dict[str, Any]] = []
        all_target_names: List[str] = []

        for target_name, endpoints in targets_data.items():
            all_target_names.append(target_name)
            all_endpoints.extend(endpoints)

        total_targets = len(targets_data)
        total_endpoints = len(all_endpoints)

        # Patrones compartidos entre targets
        assistant_output = self._assistant.correlate_cross_target_patterns(targets_data)

        cross_patterns = self._extract_cross_patterns(targets_data)

        # Vulnerabilidades en tendencia
        all_vuln_types: List[str] = []
        if hypotheses_by_target:
            for hyps in hypotheses_by_target.values():
                for h in hyps:
                    vt = getattr(h, "vulnerability_type", None)
                    if vt and hasattr(vt, "value"):
                        all_vuln_types.append(vt.value)
        type_counts = Counter(all_vuln_types)
        trending = []
        for vt, count in type_counts.most_common(8):
            targets_with = []
            if hypotheses_by_target:
                for tid, hyps in hypotheses_by_target.items():
                    if any(getattr(h, "vulnerability_type", None) and getattr(h.vulnerability_type, "value", "") == vt for h in hyps):
                        targets_with.append(str(tid))
            trending.append(TrendingVulnerability(
                vulnerability_type=vt,
                count=count,
                targets_affected=targets_with,
                avg_risk_score=0.0,
            ))

        # Valor total estimado
        estimated_payouts = [float(ep.get("risk_score", 0) * 50) for ep in all_endpoints]
        estimated_total_value = sum(estimated_payouts)

        # Top recomendación
        if trending:
            top_trend = trending[0]
            top_rec = f"Enfoque en {top_trend.vulnerability_type}: detectado en {top_trend.count} hipótesis entre {len(top_trend.targets_affected)} targets"
        else:
            top_rec = "Ejecuta el Hypothesis Engine en targets priorizados para generar inteligencia"

        return IntelligenceReport(
            total_targets=total_targets,
            total_endpoints=total_endpoints,
            estimated_total_value=round(estimated_total_value, 2),
            trending_vulnerabilities=trending[:5],
            cross_target_patterns=cross_patterns[:5],
            top_recommendation=top_rec,
            summary=assistant_output[:500] if assistant_output else "Sin datos suficientes para correlación",
        )

    def _extract_cross_patterns(
        self, targets_data: Dict[str, List[Dict[str, Any]]]
    ) -> List[CrossTargetPattern]:
        patterns: Dict[str, Set[str]] = defaultdict(set)
        total_endpoints: Dict[str, int] = defaultdict(int)
        total_risk: Dict[str, float] = defaultdict(float)

        for target_name, endpoints in targets_data.items():
            for ep in endpoints:
                path = str(ep.get("path", "/"))
                parts = path.split("/")
                if len(parts) >= 3:
                    pattern = "/".join(parts[:3]) + "/*"
                    patterns[pattern].add(target_name)
                    total_endpoints[pattern] += 1
                    total_risk[pattern] += float(ep.get("risk_score", 0))

        result = []
        for pattern, targets in patterns.items():
            if len(targets) >= 2:
                avg_risk = total_risk[pattern] / max(total_endpoints[pattern], 1)
                result.append(CrossTargetPattern(
                    pattern=pattern,
                    targets=sorted(targets),
                    endpoint_count=total_endpoints[pattern],
                    avg_risk=round(avg_risk, 1),
                ))

        return sorted(result, key=lambda p: len(p.targets), reverse=True)

    def generate_insights(
        self,
        target_name: str,
        endpoints: List[Dict[str, Any]],
        verdicts: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Genera narrativa de riesgo para un target específico."""
        return self._assistant.risk_narrative(target_name, endpoints, verdicts)
