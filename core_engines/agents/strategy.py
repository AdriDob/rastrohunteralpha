"""StrategyAgent — prioritizes work by expected ROI."""

from __future__ import annotations

import logging
from typing import Any

from core_engines.agents.base import BaseAgent
from core_engines.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("rastro.agents.strategy")


class StrategyAgent(BaseAgent):
    """Prioritizes work by expected ROI.

    Uses the existing opportunity scoring, ROI estimation, and priority engine.
    Provides ranked recommendations to the user and coordinator.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._recommendations: list[dict[str, Any]] = []

    def _get_agent_id(self) -> AgentId:
        return AgentId.STRATEGY

    def _get_subscriptions(self) -> list[EventType | str]:
        return [
            EventType.STRATEGY_RECOMMENDATION,
            EventType.RESEARCH_COMPLETED,
            EventType.VALIDATION_COMPLETED,
            EventType.DOCUMENTATION_COMPLETED,
        ]

    def handle_event(self, event: AgentEvent) -> None:
        handler_map = {
            EventType.RESEARCH_COMPLETED: self._on_research_completed,
            EventType.VALIDATION_COMPLETED: self._on_validation_completed,
            EventType.DOCUMENTATION_COMPLETED: self._on_documentation_completed,
            EventType.STRATEGY_RECOMMENDATION: self._generate_recommendation,
        }
        handler = handler_map.get(event.event_type)
        if handler:
            handler(event)

    def _on_research_completed(self, event: AgentEvent) -> None:
        """After discovery, estimate ROI of found endpoints."""
        endpoints = event.payload.get("endpoints", [])
        target_name = event.payload.get("target_name", "")

        roi_estimates = []
        for ep in endpoints[:20]:
            risk = ep.get("risk_score", 0.5)
            roi_estimates.append({
                "path": ep.get("path", "/"),
                "method": ep.get("method", "GET"),
                "risk_score": round(risk, 2),
                "estimated_roi": round(risk * 100, 1),  # Simplified ROI
            })

        logger.info("[STRATEGY] Estimated ROI for %d endpoints on %s",
                    len(roi_estimates), target_name)

    def _on_validation_completed(self, event: AgentEvent) -> None:
        confirmed = event.payload.get("confirmed_count", 0)
        if confirmed > 0:
            logger.info("[STRATEGY] %d confirmed findings — high priority pipeline",
                        confirmed)

    def _on_documentation_completed(self, event: AgentEvent) -> None:
        reports = event.payload.get("reports", [])
        if reports:
            best = max(reports, key=lambda r: r.get("bounty_estimate", 0))
            rec = {
                "type": "report_ready_for_review",
                "target": event.payload.get("target_name", ""),
                "title": best.get("title", ""),
                "severity": best.get("severity", ""),
                "bounty_estimate": best.get("bounty_estimate", 0),
                "priority": "high" if best.get("bounty_estimate", 0) > 500 else "medium",
            }
            self._recommendations.append(rec)
            self._emit_recommendation(rec, event.correlation_id)

    def _generate_recommendation(self, event: AgentEvent) -> None:
        """Generate strategic recommendations based on system state."""
        try:
            from core_engines.opportunity.engine import OpportunityEngine
            engine = OpportunityEngine()
            opportunities = engine.get_top_opportunities(limit=5)

            for opp in opportunities:
                rec = {
                    "type": "opportunity",
                    "target": opp.get("name", ""),
                    "platform": opp.get("platform", ""),
                    "estimated_payout": opp.get("payout", 0),
                    "evh": opp.get("evh", 0),
                    "priority": "high" if opp.get("evh", 0) > 50 else "medium",
                }
                self._recommendations.append(rec)
                self._emit_recommendation(rec, event.correlation_id)
        except Exception as exc:
            logger.warning("[STRATEGY] Opportunity scoring failed: %s", exc)

    def _emit_recommendation(self, rec: dict[str, Any], correlation_id: str) -> None:
        self.emit(
            EventType.STRATEGY_RECOMMENDATION,
            payload={"recommendation": rec},
            target=AgentId.COORDINATOR,
            correlation_id=correlation_id,
        )

    def get_recommendations(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._recommendations[-limit:]


_STRATEGY: StrategyAgent | None = None


def get_strategy_agent() -> StrategyAgent:
    global _STRATEGY
    if _STRATEGY is None:
        _STRATEGY = StrategyAgent()
    return _STRATEGY
