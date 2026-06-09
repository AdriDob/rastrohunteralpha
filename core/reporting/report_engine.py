from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.evidence.store import EvidenceStore
from core.reporting.export_formats import ExportFormats
from core.reporting.severity import cvss_vector, risk_to_severity, severity_score
from core.validation.gate import Verdict


@dataclass
class ProgramData:
    name: str = "Private Program"
    platform: str = "hackerone"
    bounty_range: str = "$500 - $5,000"
    in_scope: bool = True


@dataclass
class FinalReport:
    verdict_id: str
    title: str
    narrative: str
    severity: str
    cvss: str
    severity_score: float
    bounty_estimate: str
    affected_endpoint: str
    attack_vector: str
    reproduction_steps: List[str]
    evidence: List[Dict[str, Any]]
    poc_curl: str
    remediation: str
    export_formats: Dict[str, str]


class ReportEngine:
    def __init__(self, evidence_store: Optional[EvidenceStore] = None):
        self._evidence_store = evidence_store or EvidenceStore()
        self._exporters = ExportFormats()

    def build(
        self,
        verdict: Verdict,
        program_data: Optional[ProgramData] = None,
        endpoint_data: Optional[Dict[str, Any]] = None,
        evidence_list: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[FinalReport]:
        from core.validation.gate import ReportGate
        if not ReportGate().admit(verdict):
            return None

        prog = program_data or ProgramData()
        ep = endpoint_data or {}
        if evidence_list is not None:
            evidence = evidence_list
        else:
            evidence = self._evidence_store.get_evidence_for_verdict(
                int(verdict.hot_path_id.split(":")[-1]) if ":" in verdict.hot_path_id else 0
            )

        severity = risk_to_severity(ep.get("risk_score", 65))
        cvss = cvss_vector(ep.get("risk_score", 65))
        sev_score = severity_score(severity)

        title = self._build_title(verdict, ep)
        narrative = self._build_narrative(verdict, ep, severity)
        reproduction = self._build_reproduction_steps(verdict, evidence)
        poc_curl = self._build_poc_curl(evidence)

        return FinalReport(
            verdict_id=verdict.hot_path_id,
            title=title,
            narrative=narrative,
            severity=severity,
            cvss=cvss,
            severity_score=sev_score,
            bounty_estimate=prog.bounty_range,
            affected_endpoint=ep.get("path", "/unknown"),
            attack_vector=verdict.validation.passed_rules[0] if verdict.validation.passed_rules else "unknown",
            reproduction_steps=reproduction,
            evidence=evidence,
            poc_curl=poc_curl,
            remediation=self._remediation(verdict.validation.passed_rules),
            export_formats=self._exporters.generate_all(
                title=title,
                narrative=narrative,
                severity=severity,
                cvss=cvss,
                cvss_score=ep.get("cvss_score"),
                affected_endpoint=ep.get("path", "/unknown"),
                affected_method=ep.get("method", "GET"),
                reproduction_steps=reproduction,
                poc_curl=poc_curl,
                remediation=self._remediation(verdict.validation.passed_rules),
                program=prog.name,
                platform=prog.platform,
            ),
        )

    def _build_title(self, verdict: Verdict, ep: Dict[str, Any]) -> str:
        path = ep.get("path", "/unknown")
        method = ep.get("method", "GET")
        rules = verdict.validation.passed_rules
        if "privilege_boundary_break" in rules:
            return f"IDOR / Privilege Boundary Break in {method} {path}"
        if "auth_bypass" in rules:
            return f"Authentication Bypass in {method} {path}"
        if "sensitive_data_exposure" in rules:
            return f"Sensitive Data Exposure in {method} {path}"
        if "cross_session_mismatch" in rules:
            return f"Cross-Session Data Mismatch in {method} {path}"
        return f"Security Finding in {method} {path}"

    def _build_narrative(self, verdict: Verdict, ep: Dict[str, Any], severity: str) -> str:
        path = ep.get("path", "/unknown")
        method = ep.get("method", "GET")
        rules = ", ".join(verdict.validation.passed_rules) or "none"
        return (
            f"During automated security validation of {method} {path}, "
            f"the following rule(s) confirmed the finding: {rules}. "
            f"Confidence: {verdict.confidence:.0%} ({verdict.confidence_details.level}). "
            f"Reproducibility: {verdict.reproducibility_score:.0%} across {verdict.retry_count} independent attempts. "
            f"Severity: {severity.upper()}. "
            f"All attempts were executed with authenticated sessions, "
            f"comparing baseline (owner context) vs probe (modified context) responses."
        )

    def _build_reproduction_steps(self, verdict: Verdict, evidence: List[Dict[str, Any]]) -> List[str]:
        steps = [
            f"1. Authenticate as user A (baseline context).",
            f"2. Send the baseline request and record the response.",
        ]
        if evidence:
            for idx, ev in enumerate(evidence[:3]):
                status = ev.get("response_status", "?")
                steps.append(
                    f"{3 + idx}. Send probe request (attempt {ev.get('attempt', idx + 1)}) — "
                    f"response status: {status}."
                )
            next_idx = 3 + len(evidence[:3])
        else:
            next_idx = 3
        steps.append(f"{next_idx}. Compare baseline vs probe responses.")
        steps.append(f"{next_idx + 1}. Repeat steps 2-4 at least {verdict.retry_count} times to confirm reproducibility.")
        steps.append(f"{next_idx + 2}. If responses differ consistently, the finding is confirmed.")
        return steps

    def _build_poc_curl(self, evidence: List[Dict[str, Any]]) -> str:
        for ev in evidence:
            if ev.get("curl_command"):
                return ev["curl_command"]
        return "curl -X GET '<affected_url>' -H 'Authorization: Bearer <token>'"

    def _remediation(self, passed_rules: List[str]) -> str:
        if "privilege_boundary_break" in passed_rules:
            return (
                "Implement proper access control checks on the server side. "
                "Verify that the authenticated user owns or has permissions for the requested resource. "
                "Use indirect object references (e.g., GUIDs) instead of sequential IDs, "
                "but always combine with server-side authorization checks."
            )
        if "auth_bypass" in passed_rules:
            return (
                "Ensure all authenticated endpoints verify the validity of the session token "
                "or authentication header before processing the request. "
                "Implement consistent authentication middleware that cannot be bypassed "
                "by simply removing or modifying headers."
            )
        if "sensitive_data_exposure" in passed_rules:
            return (
                "Remove sensitive fields (PII, financial data, credentials) from API responses. "
                "Implement field-level access control and use response filtering "
                "based on user roles and permissions. Consider using GraphQL field allowlists."
            )
        if "cross_session_mismatch" in passed_rules:
            return (
                "Ensure that responses are consistent across different user sessions "
                "for the same resource. If data varies by user context, verify "
                "that the variation is intentional and authorized."
            )
        return "Review the affected endpoint and implement appropriate security controls."
