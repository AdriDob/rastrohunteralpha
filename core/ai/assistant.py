from typing import Any, Dict, List, Optional

from core.evidence.graph import EvidenceGraph
from core.reporting.report_engine import FinalReport, ReportEngine
from core.reporting.severity import confidence_to_label, risk_to_severity


class ScanAssistant:
    def __init__(
        self,
        evidence_graph: Optional[EvidenceGraph] = None,
        report_engine: Optional[ReportEngine] = None,
        scorer=None,
    ):
        self._evidence_graph = evidence_graph or EvidenceGraph()
        self._report_engine = report_engine or ReportEngine()

    def summarize_scan(self, scan_id: str, endpoint_count: int = 0, verdicts: Optional[List[Dict[str, Any]]] = None, reports: Optional[List[FinalReport]] = None) -> str:
        verdicts = verdicts or self._evidence_graph.get_verdicts()
        reports = reports or []

        confirmed = [v for v in verdicts if v.get("status") == "confirmed"]
        rejected = [v for v in verdicts if v.get("status") == "rejected"]
        inconclusive = [v for v in verdicts if v.get("status") == "inconclusive"]

        lines: List[str] = []
        lines.append(f"## Scan Summary: {scan_id}")
        lines.append(f"")
        lines.append(f"**Endpoints analyzed:** {endpoint_count}")
        lines.append(f"**Verdicts:** {len(verdicts)} total "
                      f"({len(confirmed)} confirmed, {len(inconclusive)} inconclusive, {len(rejected)} rejected)")
        lines.append(f"**Reports generated:** {len(reports)}")
        lines.append(f"")

        if confirmed:
            lines.append("### Confirmed Findings")
            for v in confirmed[:10]:
                hp_id = v.get("hot_path_id", "unknown")
                confidence = v.get("confidence", 0)
                label = confidence_to_label(confidence)
                lines.append(f"- `{hp_id}` — confidence {confidence:.0%} ({label})")
            if len(confirmed) > 10:
                lines.append(f"- ... and {len(confirmed) - 10} more")

        if reports:
            lines.append("")
            lines.append("### Reports Ready for Submission")
            for r in reports[:5]:
                lines.append(f"- **{r.severity.upper()}** {r.title} → `{r.affected_endpoint}`")
            if len(reports) > 5:
                lines.append(f"- ... and {len(reports) - 5} more")

        return "\n".join(lines)

    def explain_finding(self, finding_id: str, verdict: Optional[Dict[str, Any]] = None, report: Optional[FinalReport] = None, evidence_graph: Optional[EvidenceGraph] = None) -> str:
        graph = evidence_graph or self._evidence_graph

        lines: List[str] = []
        lines.append(f"## Finding Analysis: {finding_id}")
        lines.append("")

        if verdict:
            status = verdict.get("status", "unknown")
            confidence = verdict.get("confidence", 0)
            reason = verdict.get("reason", "No reason provided")
            passed = verdict.get("passed_rules", []) or []
            failed = verdict.get("failed_rules", []) or []

            lines.append(f"**Status:** {status}")
            lines.append(f"**Confidence:** {confidence:.0%} ({confidence_to_label(confidence)})")
            lines.append(f"**Rules passed:** {', '.join(passed) if passed else 'none'}")
            lines.append(f"**Rules failed:** {', '.join(failed) if failed else 'none'}")
            lines.append(f"**Reason:** {reason}")
            lines.append("")

            if passed:
                lines.append("### What this means")
                for rule in passed:
                    explanation = self._rule_explanation(rule)
                    lines.append(f"- **{rule}** — {explanation}")

            lines.append("")
            comparison_nodes = graph.get_nodes_by_type("comparison")
            related = [n for n in comparison_nodes if finding_id in n.get("hot_path_id", "")]
            if related:
                lines.append(f"### Evidence ({len(related)} comparisons)")
                for comp in related[:5]:
                    lines.append(f"- Attempt {comp.get('attempt')}: "
                                 f"status_match={comp.get('status_match')}, "
                                 f"body_diff={comp.get('body_diff_ratio', 0):.2%}")
                lines.append("")
                consistent = sum(1 for c in related if c.get("consistent"))
                lines.append(f"**Consistency:** {consistent}/{len(related)} attempts reliable")

        if report:
            lines.append("")
            lines.append(f"### Report Summary")
            lines.append(f"**Title:** {report.title}")
            lines.append(f"**Severity:** {report.severity.upper()} (CVSS: {report.cvss})")
            lines.append(f"**Endpoint:** {report.affected_endpoint}")
            lines.append(f"**Attack vector:** {report.attack_vector}")
            lines.append(f"**Remediation:** {report.remediation}")

        return "\n".join(lines)

    def suggest_next_targets(self, investigation_graph: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
        nodes = investigation_graph.get("nodes", [])
        edges = investigation_graph.get("edges", [])

        endpoint_nodes = [n for n in nodes if n.get("type") == "endpoint"]
        entity_nodes = [n for n in nodes if n.get("type") == "entity"]

        scored: List[Dict[str, Any]] = []
        for ep in endpoint_nodes:
            meta = ep.get("metadata", {})
            risk = float(meta.get("risk_score", 0))
            signal_count = len(meta.get("signals", []))

            incoming_edges = [e for e in edges if e.get("to") == ep.get("node_id")]
            entity_bridge = any(e.get("relationship") in ("references", "shares_entity") for e in incoming_edges)

            priority = risk + (signal_count * 5) + (10 if entity_bridge else 0)

            scored.append({
                "node_id": ep["node_id"],
                "value": ep.get("value", ""),
                "priority_score": round(priority, 1),
                "risk_score": risk,
                "signals": meta.get("signals", []),
                "entity_bridge": entity_bridge,
            })

        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        return scored[:top_n]

    def risk_narrative(self, target_name: str, endpoints: List[Dict[str, Any]], verdicts: Optional[List[Dict[str, Any]]] = None) -> str:
        verdicts = verdicts or []

        total = len(endpoints)
        if total == 0:
            return f"## Risk Narrative: {target_name}\n\nNo endpoints analyzed for this target."

        avg_risk = sum(float(e.get("risk_score", 0)) for e in endpoints) / total
        confirmed = [v for v in verdicts if v.get("status") == "confirmed"]
        high_risk = [e for e in endpoints if float(e.get("risk_score", 0)) >= 65]

        severity = risk_to_severity(avg_risk)

        lines: List[str] = []
        lines.append(f"## Risk Narrative: {target_name}")
        lines.append("")
        lines.append(f"**Overall risk posture:** {severity.upper()} (avg score {avg_risk:.0f}/100)")
        lines.append(f"**Total endpoints:** {total}")
        lines.append(f"**High-risk endpoints:** {len(high_risk)}")
        lines.append(f"**Confirmed findings:** {len(confirmed)}")
        lines.append("")

        if high_risk:
            lines.append("### High-Risk Areas")
            for ep in high_risk[:10]:
                path = ep.get("path", "/")
                method = ep.get("method", "GET")
                score = ep.get("risk_score", 0)
                surfaces = ep.get("attack_surface", [])
                lines.append(f"- `{method} {path}` — score {score} ({', '.join(surfaces) or 'no surface'})")

        if confirmed:
            lines.append("")
            lines.append("### Active Vulnerabilities")
            for v in confirmed[:5]:
                hp_id = v.get("hot_path_id", "?")
                conf = v.get("confidence", 0)
                lines.append(f"- `{hp_id}` — confidence {conf:.0%}")

        lines.append("")
        lines.append("### Recommendation")
        if severity in ("critical", "high"):
            lines.append("Immediate investigation required. High-risk endpoints with active "
                         "findings should be prioritized for manual verification and responsible disclosure.")
        elif severity == "medium":
            lines.append("Moderate risk posture. Review high-risk endpoints and validate "
                         "findings before proceeding to manual exploitation.")
        else:
            lines.append("Low risk posture. Continue monitoring for changes in attack surface.")

        return "\n".join(lines)

    def correlate_cross_target_patterns(self, target_data: Dict[str, List[Dict[str, Any]]]) -> str:
        all_patterns: Dict[str, List[str]] = {}

        for target_name, endpoints in target_data.items():
            for ep in endpoints:
                path = str(ep.get("path", "/"))
                method = str(ep.get("method", "GET"))
                path_part = "/".join(path.split("/")[:3])
                key = f"{method} {path_part}/*"
                if key not in all_patterns:
                    all_patterns[key] = []
                all_patterns[key].append(target_name)

        lines: List[str] = []
        lines.append("## Cross-Target Pattern Correlation")
        lines.append("")

        shared = {k: v for k, v in all_patterns.items() if len(v) >= 2}
        if shared:
            lines.append(f"### Shared API Patterns ({len(shared)} found)")
            for pattern, targets in sorted(shared.items(), key=lambda x: -len(x[1])):
                lines.append(f"- `{pattern}` — shared by {', '.join(targets)}")

        lines.append("")
        lines.append(f"### Unique Patterns ({len(all_patterns) - len(shared)}) per target")

        return "\n".join(lines)

    @staticmethod
    def _rule_explanation(rule: str) -> str:
        explanations = {
            "privilege_boundary_break": (
                "Response contains sensitive data that differs between user contexts. "
                "This indicates a user A can access resources belonging to user B by "
                "modifying an object reference parameter."
            ),
            "auth_bypass": (
                "Probe request without authentication returns the same response as "
                "the authenticated baseline. The endpoint does not enforce authentication."
            ),
            "sensitive_data_exposure": (
                "Response contains PII, financial data, or credentials (email, SSN, "
                "credit card, JWT). Sensitive fields are exposed to the client."
            ),
            "cross_session_mismatch": (
                "Response body differs significantly between sessions. Possible data "
                "leak or session confusion vulnerability."
            ),
        }
        return explanations.get(rule, "Validation rule triggered. Review the evidence for details.")
