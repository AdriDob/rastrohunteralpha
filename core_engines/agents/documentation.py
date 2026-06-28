"""DocumentationAgent — produces production-quality reports."""

from __future__ import annotations

import logging
from typing import Any

from core_engines.agents.base import BaseAgent
from core_engines.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("rastro.agents.documentation")


class DocumentationAgent(BaseAgent):
    """Generates production-quality bug bounty reports.

    Uses the existing ReportEngine to produce:
    - HackerOne JSON
    - Bugcrowd HTML
    - Markdown
    - CVSS scoring
    - CWE mapping
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_agent_id(self) -> AgentId:
        return AgentId.DOCUMENTATION

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.DOCUMENTATION_REQUESTED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.DOCUMENTATION_REQUESTED:
            self._generate(event)

    def _generate(self, event: AgentEvent) -> None:
        confirmed = event.payload.get("confirmed", {})
        target_id = event.payload.get("target_id", 0)
        target_name = event.payload.get("target_name", "")
        pipeline_id = event.correlation_id

        if not confirmed:
            logger.info("[DOC] No confirmed findings to document for %s", target_name)
            self.emit(
                EventType.DOCUMENTATION_COMPLETED,
                payload={"target_id": target_id, "target_name": target_name,
                         "reports": [], "stage": "documentation",
                         "next_stage": "ready", "pipeline_id": pipeline_id},
                target=AgentId.COORDINATOR,
                correlation_id=pipeline_id,
            )
            return

        reports = []
        try:
            from core_engines.evidence.store import EvidenceStore
            from core_engines.reporting.report_engine import ProgramData, ReportEngine

            store = EvidenceStore()
            engine = ReportEngine(evidence_store=store)

            for hp_key, data in confirmed.items():
                if not data.get("confirmed"):
                    continue

                # Build a minimal verdict-like object for the report engine
                class VerdictProxy:
                    def __init__(self, d: dict[str, Any], path_id: str):
                        self.hot_path_id = path_id
                        self.status = "confirmed"
                        self.confidence = d.get("confidence", 0.7)
                        self.reason = d.get("exploit_detail", "Confirmed via differential analysis")
                        self.validation = self._make_validation(d)

                    @staticmethod
                    def _make_validation(d: dict[str, Any]) -> Any:
                        class V:
                            passed_rules = ["differential_match"]
                            failed_rules = []
                        return V()

                proxy = VerdictProxy(data, hp_key)
                program = ProgramData(
                    name=target_name,
                    platform="hackerone",
                    scope=f"https://{target_name}/",
                    in_scope=True,
                )

                evidence_list = []
                if data.get("evidence_id"):
                    ev = store.get_evidence(data["evidence_id"])
                    if ev:
                        evidence_list.append(ev)

                ep_data = {
                    "url": f"https://{target_name}{data.get('path', '/')}",
                    "method": data.get("method", "GET"),
                    "path": data.get("path", "/"),
                }

                report = engine.build(
                    proxy, program_data=program,
                    endpoint_data=ep_data, evidence_list=evidence_list,
                )
                if report:
                    reports.append({
                        "title": report.title,
                        "severity": report.severity,
                        "cvss": report.cvss,
                        "cwe": getattr(report, 'cwe', ""),
                        "bounty_estimate": report.bounty_estimate,
                        "formats": {
                            "hackerone_json": getattr(report, 'hackerone_json', ""),
                            "markdown": getattr(report, 'markdown', ""),
                            "bugcrowd_html": getattr(report, 'bugcrowd_html', ""),
                        },
                    })

            logger.info("[DOC] Generated %d reports for %s", len(reports), target_name)

        except Exception as exc:
            logger.error("[DOC] Report generation failed: %s", exc)

        self.emit(
            EventType.DOCUMENTATION_COMPLETED,
            payload={
                "target_id": target_id, "target_name": target_name,
                "reports": reports, "reports_count": len(reports),
                "stage": "documentation",
                "next_stage": "ready",
                "pipeline_id": pipeline_id,
            },
            target=AgentId.COORDINATOR,
            correlation_id=pipeline_id,
        )
