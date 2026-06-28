"""ResearchAgent — discovers targets, programs, and attack surface."""

from __future__ import annotations

import logging

from core_engines.agents.base import BaseAgent
from core_engines.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("rastro.agents.research")


class ResearchAgent(BaseAgent):
    """Discovers new targets, programs, endpoints, and attack surface.

    Delegates to the existing recon pipeline (subfinder, httpx, katana, etc.).
    Publishes discovered endpoints for validation.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_agent_id(self) -> AgentId:
        return AgentId.RESEARCH

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.RESEARCH_START]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.RESEARCH_START:
            self._run_discovery(event)

    def _run_discovery(self, event: AgentEvent) -> None:
        target_name = event.payload.get("target_name", "")
        target_id = event.payload.get("target_id", 0)
        pipeline_id = event.correlation_id
        logger.info("[RESEARCH] Starting discovery for %s", target_name)

        endpoints = []

        # Phase 1: Subdomain enumeration
        if target_name:
            try:
                from core_engines.recon.subfinder_runner import run_subfinder
                subdomains = run_subfinder(target_name)
                for sd in (subdomains or []):
                    endpoints.append({
                        "path": f"https://{sd}/",
                        "method": "GET",
                        "params": {},
                        "source": "subfinder",
                    })
                logger.info("[RESEARCH] subfinder found %d subdomains for %s",
                            len(subdomains or []), target_name)
            except Exception as exc:
                logger.warning("[RESEARCH] subfinder failed: %s", exc)

        # Phase 2: HTTP probing
        if endpoints:
            try:
                from core_engines.recon.httpx_runner import run_httpx
                urls = [e["path"] for e in endpoints[:50]]  # Limit for performance
                live = run_httpx(urls)
                endpoints = [e for e in endpoints if e["path"] in (live or [])]
                logger.info("[RESEARCH] httpx confirmed %d live endpoints", len(endpoints))
            except Exception as exc:
                logger.warning("[RESEARCH] httpx failed: %s", exc)

        # Phase 3: Path discovery
        if endpoint_paths := [e["path"] for e in endpoints[:20]]:
            try:
                from core_engines.recon.katana_runner import run_katana
                paths = run_katana(endpoint_paths)
                for p in (paths or []):
                    if isinstance(p, str) and p not in {e["path"] for e in endpoints}:
                        endpoints.append({
                            "path": p, "method": "GET", "params": {},
                            "source": "katana",
                        })
                logger.info("[RESEARCH] katana found %d additional paths", len(paths or []))
            except Exception as exc:
                logger.warning("[RESEARCH] katana failed: %s", exc)

        # Publish results
        for ep in endpoints:
            self.emit(
                EventType.ENDPOINT_DISCOVERED,
                payload={"target_id": target_id, "target_name": target_name,
                         "endpoint": ep, "pipeline_id": pipeline_id},
                correlation_id=pipeline_id,
            )

        # Signal completion
        self.emit(
            EventType.RESEARCH_COMPLETED,
            payload={
                "target_id": target_id,
                "target_name": target_name,
                "endpoints_count": len(endpoints),
                "stage": "discovery",
                "next_stage": "validation",
                "pipeline_id": pipeline_id,
                "endpoints": endpoints,
            },
            target=AgentId.COORDINATOR,
            correlation_id=pipeline_id,
        )
        logger.info("[RESEARCH] Discovery completed: %d endpoints for %s",
                    len(endpoints), target_name)
