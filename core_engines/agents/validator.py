"""ValidatorAgent — determines whether findings are likely valid."""

from __future__ import annotations

import logging

from core_engines.agents.base import BaseAgent
from core_engines.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("rastro.agents.validator")


class ValidatorAgent(BaseAgent):
    """Evaluates findings and determines likelihood of validity.

    Uses the existing scoring engine and validation pipeline.
    Publishes validated findings for exploit confirmation.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_agent_id(self) -> AgentId:
        return AgentId.VALIDATOR

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.VALIDATION_REQUESTED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.VALIDATION_REQUESTED:
            self._validate(event)

    def _validate(self, event: AgentEvent) -> None:
        endpoints = event.payload.get("endpoints", [])
        target_id = event.payload.get("target_id", 0)
        target_name = event.payload.get("target_name", "")
        pipeline_id = event.correlation_id

        if not endpoints:
            logger.info("[VALIDATOR] No endpoints to validate for %s", target_name)
            self.emit(
                EventType.VALIDATION_COMPLETED,
                payload={"target_id": target_id, "target_name": target_name,
                         "verdicts": {}, "stage": "validation",
                         "next_stage": "evidence", "pipeline_id": pipeline_id},
                target=AgentId.COORDINATOR,
                correlation_id=pipeline_id,
            )
            return

        # Run scoring engine on endpoints
        scored = []
        try:
            from core_engines.engine.unified_scoring import score as unified_score
            for ep in endpoints:
                path = str(ep.get("path", "/"))
                method = str(ep.get("method", "GET")).upper()
                params = ep.get("params", {})
                result = unified_score(path, method, params)
                result["path"] = path
                result["method"] = method
                result["params"] = params
                scored.append(result)
        except Exception as exc:
            logger.warning("[VALIDATOR] Scoring failed: %s", exc)
            scored = endpoints

        # Run noise reduction
        try:
            from core_engines.analysis.noise_reduction import NoiseReductionEngine
            filtered = NoiseReductionEngine().analyze(scored)
            clean = filtered.clean_endpoints
            logger.info("[VALIDATOR] Noise reduction: %d/%d clean",
                        len(clean), len(scored))
        except Exception as exc:
            logger.warning("[VALIDATOR] Noise reduction failed: %s", exc)
            clean = scored

        # Build verdicts (simplified — full pipeline uses differential engine)
        verdicts = {}
        for idx, ep in enumerate(clean[:20]):  # Limit for performance
            risk_score = ep.get("risk_score", 0)
            status = "confirmed" if risk_score > 0.6 else "unconfirmed"
            verdicts[f"{idx}:{ep.get('path', '/')}"] = {
                "status": status,
                "confidence": min(risk_score + 0.2, 0.99),
                "risk_score": risk_score,
                "path": ep.get("path", "/"),
                "method": ep.get("method", "GET"),
            }

        confirmed_count = sum(1 for v in verdicts.values() if v["status"] == "confirmed")

        self.emit(
            EventType.VALIDATION_COMPLETED,
            payload={
                "target_id": target_id, "target_name": target_name,
                "verdicts": verdicts, "confirmed_count": confirmed_count,
                "stage": "validation", "next_stage": "evidence",
                "pipeline_id": pipeline_id, "endpoints": clean,
            },
            target=AgentId.COORDINATOR,
            correlation_id=pipeline_id,
        )
        logger.info("[VALIDATOR] Validation completed: %d confirmed out of %d",
                    confirmed_count, len(clean))
