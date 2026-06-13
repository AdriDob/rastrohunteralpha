"""
Rastro AI Assistant — main orchestrator + ScanAssistant.

ScanAssistant: original rule-based assistant for scan analysis, findings, risk narratives.
Assistant: new unified orchestrator with context, insights, recommendations, chat.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core_engines.ai.context_builder import build_full_context
from core_engines.ai.insights import generate_insights, get_top_insight
from core_engines.ai.recommendations import generate_recommendations, get_best_recommendation
from core_engines.ai.advisor import answer_query
from core_engines.ai.summary import daily_summary, system_status
from core_engines.ai.memory import get_memory, save_interaction, get_recent_interactions
from core_engines.ai.provider import get_provider
from core_engines.evidence.graph import EvidenceGraph
from core_engines.reporting.report_engine import FinalReport, ReportEngine
from core_engines.reporting.severity import confidence_to_label, risk_to_severity

logger = logging.getLogger("rastro.ai.assistant")


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

    def explain_differential(
        self,
        differential_bundle=None,
    ) -> str:
        """
        Generate a narrative explanation of differential intelligence findings.
        Does NOT convert differences into vulnerabilities.
        """
        if differential_bundle is None:
            return "## Differential Intelligence\n\nNo differential data available."

        from core_engines.engines import DifferentialBundle
        if not isinstance(differential_bundle, DifferentialBundle):
            return "## Differential Intelligence\n\nInvalid differential data."

        lines: List[str] = []
        lines.append("## Differential Intelligence Summary")
        lines.append("")
        lines.append(differential_bundle.summary)
        lines.append("")

        all_findings: List[Any] = []
        for field_name in (
            "target_differences", "endpoint_differences", "historical_changes",
            "cross_target_patterns", "web3_differences", "interesting_anomalies",
        ):
            all_findings.extend(getattr(differential_bundle, field_name, []))

        if not all_findings:
            lines.append("No meaningful differences detected in this analysis.")
            return "\n".join(lines)

        # Group by category
        by_cat: Dict[str, List[Any]] = {}
        for f in all_findings:
            cat = getattr(f, "category", "general")
            by_cat.setdefault(cat, []).append(f)

        for cat, items in sorted(by_cat.items()):
            high_risk = [f for f in items if getattr(f, "risk_level", "low") in ("high", "critical")]
            lines.append(f"### {cat.title()} ({len(items)} observation{'' if len(items) == 1 else 's'})")
            for item in items[:5]:
                title = getattr(item, "title", "Unknown")
                risk = getattr(item, "risk_level", "low")
                conf = getattr(item, "confidence", 0)
                desc = getattr(item, "description", "")
                objects = getattr(item, "affected_objects", [])
                objs_str = ", ".join(objects[:3]) if objects else ""
                requires = getattr(item, "requires_validation", True)
                lines.append(
                    f"- **{title}** (risk: {risk}, confidence: {conf:.0%})"
                    + (f" — {objs_str}" if objs_str else "")
                )
                if desc:
                    lines.append(f"  {desc[:200]}")
                if requires:
                    lines.append("  ⚠ Requires human validation — observation only, not a finding.")
            if len(items) > 5:
                lines.append(f"  ... and {len(items) - 5} more")
            lines.append("")

        if differential_bundle.interesting_anomalies:
            lines.append("### Recommended Review Priority")
            for a in differential_bundle.interesting_anomalies[:3]:
                lines.append(
                    f"- [{getattr(a, 'validation_priority', 'low').upper()}] "
                    f"{getattr(a, 'title', 'Unknown')}"
                )

        lines.append("")
        lines.append("*These are observations derived from existing pipeline data. "
                     "They do not constitute vulnerability findings and require human validation.*")

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


class Assistant:
    def __init__(self):
        self.memory = get_memory()
        self.provider = get_provider()

    def chat(self, message: str) -> Dict[str, Any]:
        self.memory.add("user", message)
        save_interaction("user", message)

        result = answer_query(message)
        answer = result.get("answer", "")
        source = result.get("source", "local/rules")

        self.memory.add("assistant", answer)
        save_interaction("assistant", answer)

        return {
            "answer": answer,
            "source": source,
            "context": result.get("context_summary", {}),
            "suggestions": self._generate_suggestions(answer),
        }

    def _generate_suggestions(self, last_answer: str) -> List[str]:
        suggestions = [
            "¿Qué target tiene mejor ROI?",
            "¿Qué cambió hoy?",
            "¿Qué oportunidades puedo completar en dos horas?",
        ]
        last_lower = last_answer.lower()
        if "recomendación" in last_lower or "atacar" in last_lower:
            suggestions.insert(0, "¿Qué reporte está casi listo?")
        if "cambio" in last_lower or "nuevo" in last_lower:
            suggestions.insert(0, "¿Qué cambió desde el último análisis?")
        if "scan" in last_lower or "escaneo" in last_lower:
            suggestions.insert(0, "¿Qué scan terminó?")
        return suggestions[:4]

    def get_context(self) -> Dict[str, Any]:
        ctx = build_full_context()
        ctx["provider"] = self.provider.name
        return ctx

    def get_insights(self) -> List[Dict[str, Any]]:
        return generate_insights()

    def get_recommendations(self) -> List[Dict[str, Any]]:
        return generate_recommendations()

    def get_top_insight(self) -> Dict[str, Any]:
        return get_top_insight()

    def get_best_recommendation(self) -> Dict[str, Any]:
        return get_best_recommendation()

    def get_summary(self) -> Dict[str, Any]:
        return daily_summary()

    def get_status(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.name,
            "available": self.provider.is_available(),
            "memory_exchanges": len(self.memory.all()),
            "recent_interactions": get_recent_interactions(5),
            "system": system_status(),
        }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return get_recent_interactions(limit)

    def clear_memory(self) -> None:
        self.memory.clear()


_assistant_instance: Optional[Assistant] = None


def get_assistant() -> Assistant:
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = Assistant()
    return _assistant_instance
