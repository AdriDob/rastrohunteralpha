"""
differential.engine — Differential Analysis Engine.

Compara respuestas HTTP para detectar:
  - Diferencias auth vs no-auth
  - Diferencias entre roles
  - Filtración de datos en responses
  - Patrones IDOR
  - Inconsistencias basadas en parámetros

Alimenta Hypothesis Engine con señales diferenciales.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

LOG = logging.getLogger("rastro.differential")


@dataclass
class DiffComparison:
    label: str
    status_match: bool
    body_diff_ratio: float
    body_diff_sections: List[str] = field(default_factory=list)
    header_diffs: Dict[str, Tuple[Optional[str], Optional[str]]] = field(default_factory=dict)
    consistent: bool = False
    leaked_fields: List[str] = field(default_factory=list)


@dataclass
class DiffResult:
    endpoint_id: int
    path: str
    method: str
    comparisons: List[DiffComparison] = field(default_factory=list)
    has_idor_pattern: bool = False
    has_auth_bypass: bool = False
    has_data_leak: bool = False
    confidence: float = 0.0
    summary: str = ""


SENSITIVE_PATTERNS = [
    "email", "ssn", "credit_card", "password", "jwt",
    "token", "api_key", "secret", "private_key", "session",
    "phone", "address", "dob", "passport", "bank",
]


class DifferentialAnalysisEngine:
    """Analiza diferencias entre respuestas HTTP para detectar vulnerabilidades."""

    def compare_auth_contexts(
        self,
        baseline_response: Dict[str, Any],
        probe_response: Dict[str, Any],
        endpoint_path: str = "",
        endpoint_method: str = "GET",
    ) -> DiffComparison:
        """Compara respuesta autenticada vs no autenticada."""
        baseline_body = str(baseline_response.get("body", ""))
        probe_body = str(probe_response.get("body", ""))

        ratio = SequenceMatcher(None, baseline_body, probe_body).ratio()
        diff_ratio = 1.0 - ratio

        leaked = [p for p in SENSITIVE_PATTERNS if p in baseline_body.lower() and p not in probe_body.lower()]

        sections = []
        if diff_ratio < 0.1 and baseline_body and probe_body:
            sections.append("auth_bypass: mismas respuestas con y sin autenticación")
        elif diff_ratio > 0.5 and baseline_body and probe_body:
            sections.append("data_exposure: respuesta significantemente diferente entre contextos")

        return DiffComparison(
            label="auth_vs_noauth",
            status_match=baseline_response.get("status") == probe_response.get("status"),
            body_diff_ratio=round(diff_ratio, 4),
            body_diff_sections=sections,
            consistent=diff_ratio < 0.3,
            leaked_fields=leaked,
        )

    def compare_role_contexts(
        self,
        admin_response: Dict[str, Any],
        user_response: Dict[str, Any],
    ) -> DiffComparison:
        """Compara respuesta de admin vs usuario normal."""
        admin_body = str(admin_response.get("body", ""))
        user_body = str(user_response.get("body", ""))

        ratio = SequenceMatcher(None, admin_body, user_body).ratio()
        diff_ratio = 1.0 - ratio

        leaked = [p for p in SENSITIVE_PATTERNS if p in admin_body.lower() and p not in user_body.lower()]

        sections = []
        if diff_ratio < 0.15:
            sections.append("privilege_escalation: usuario normal accede a datos de admin")

        return DiffComparison(
            label="admin_vs_user",
            status_match=admin_response.get("status") == user_response.get("status"),
            body_diff_ratio=round(diff_ratio, 4),
            body_diff_sections=sections,
            consistent=diff_ratio < 0.3,
            leaked_fields=leaked,
        )

    def compare_parameter_mutation(
        self,
        original_response: Dict[str, Any],
        mutated_response: Dict[str, Any],
        mutated_param: str = "",
    ) -> DiffComparison:
        """Compara respuesta original vs con parámetro mutado (IDOR detection)."""
        orig_body = str(original_response.get("body", ""))
        mut_body = str(mutated_response.get("body", ""))

        ratio = SequenceMatcher(None, orig_body, mut_body).ratio()

        sections = []
        if ratio > 0.85 and orig_body:
            sections.append(f"idor_candidate: cambiar {mutated_param} no alteró la respuesta")

        return DiffComparison(
            label=f"param_mutation:{mutated_param}",
            status_match=original_response.get("status") == mutated_response.get("status"),
            body_diff_ratio=round(1.0 - ratio, 4),
            body_diff_sections=sections,
            consistent=ratio > 0.8,
        )

    def analyze_endpoint(
        self,
        endpoint_id: int,
        path: str,
        method: str,
        comparisons: List[DiffComparison],
    ) -> DiffResult:
        """Agrega múltiples comparaciones en un resultado único."""
        has_idor = any("idor" in c.label or "idor" in " ".join(c.body_diff_sections) for c in comparisons)
        has_bypass = any("auth_bypass" in " ".join(c.body_diff_sections) for c in comparisons)
        has_leak = any(c.leaked_fields for c in comparisons)

        consistent_count = sum(1 for c in comparisons if c.consistent)
        confidence = consistent_count / max(len(comparisons), 1)

        summary_parts = []
        if has_idor:
            summary_parts.append("IDOR pattern detected")
        if has_bypass:
            summary_parts.append("Auth bypass detected")
        if has_leak:
            summary_parts.append("Data leakage detected")
        summary = "; ".join(summary_parts) if summary_parts else "No differential signals"

        return DiffResult(
            endpoint_id=endpoint_id,
            path=path,
            method=method,
            comparisons=comparisons,
            has_idor_pattern=has_idor,
            has_auth_bypass=has_bypass,
            has_data_leak=has_leak,
            confidence=round(confidence, 4),
            summary=summary,
        )
