from typing import Any, Dict, List, Optional

from core.validation.gate import Verdict


class ValidationError(Exception):
    """Raised when a verdict fails validation requirements."""


class ConfidenceThresholdError(ValidationError):
    """Raised when confidence is below the minimum threshold for reporting."""


class ReportGenerator:
    def draft_report(
        self,
        findings: Dict[str, str],
        verdict: Optional[Verdict] = None,
        evidence_list: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        severity = findings.get("severity", "medium")

        if verdict and verdict.confidence < 0.6:
            raise ConfidenceThresholdError(
                f"Confidence {verdict.confidence:.2f} below 0.6 threshold"
            )

        if verdict and verdict.status != "confirmed":
            raise ValidationError(
                f"Cannot generate report: verdict status is '{verdict.status}', not 'confirmed'"
            )

        passed_rules = ""
        if verdict and verdict.validation.passed_rules:
            passed_rules = "\n".join(f"- {r}" for r in verdict.validation.passed_rules)

        evidence_section = ""
        if evidence_list:
            evidence_section = "\n\n## Evidence\n"
            for idx, ev in enumerate(evidence_list[:5]):
                status = ev.get("response_status", "?")
                diff = ev.get("body_diff_ratio", "?")
                evidence_section += (
                    f"- Attempt {idx + 1}: status={status}, diff={diff}\n"
                )

        reproduction = findings.get("reproduction", "")
        if passed_rules:
            reproduction += f"\n\nValidation rules passed:\n{passed_rules}"
        if evidence_section:
            reproduction += evidence_section

        return {
            "summary": findings.get(
                "summary",
                f"Investigación de endpoint con severidad {severity}."
            ),
            "impact": findings.get(
                "impact",
                "Posible falta de validación de autorización en API o recurso."
            ),
            "reproduction": reproduction,
            "severity": severity,
            "verdict_status": verdict.status if verdict else "unknown",
            "confidence": f"{verdict.confidence:.0%}" if verdict else "unknown",
        }
