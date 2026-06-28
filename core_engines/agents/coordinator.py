"""CoordinatorAgent — orchestrates pipeline workflows, persists state to SQLite, retries failures."""

from __future__ import annotations

import contextlib
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from core_engines.agents.base import BaseAgent
from core_engines.agents.types import AgentEvent, AgentId, EventType, PipelineState
from core_engines.pipeline.state_machine import (
    build_transition,
    can_retry,
    compute_quality_score,
    get_retry_delay,
    is_terminal,
    next_stage,
    validate_transition,
)
from core_engines.settings.service import RastroMode, get_mode, get_setting

logger = logging.getLogger("rastro.agents.coordinator")

# ── Stage → Agent/Event mapping (updated for 11 states) ────────────

STAGE_TO_AGENT: dict[PipelineState, AgentId] = {
    PipelineState.DISCOVERY: AgentId.RESEARCH,
    PipelineState.VALIDATION: AgentId.VALIDATOR,
    PipelineState.EVIDENCE: AgentId.EXPLOIT,
    PipelineState.AI_REVIEW: AgentId.DOCUMENTATION,
    PipelineState.READY: AgentId.COORDINATOR,
    PipelineState.SUBMITTED: AgentId.COORDINATOR,
    PipelineState.TRIAGED: AgentId.COORDINATOR,
    PipelineState.PAID: AgentId.FINANCIAL,
    PipelineState.CLOSED: AgentId.COORDINATOR,
}

STAGE_TO_EVENT: dict[PipelineState, EventType] = {
    PipelineState.DISCOVERY: EventType.RESEARCH_START,
    PipelineState.VALIDATION: EventType.VALIDATION_REQUESTED,
    PipelineState.EVIDENCE: EventType.EXPLOIT_REQUESTED,
    PipelineState.AI_REVIEW: EventType.AI_REVIEW_REQUESTED,
    PipelineState.READY: EventType.PIPELINE_STAGE_COMPLETED,
    PipelineState.SUBMITTED: EventType.SUBMISSION_REQUESTED,
    PipelineState.TRIAGED: EventType.PIPELINE_STAGE_COMPLETED,
    PipelineState.PAID: EventType.FINANCIAL_UPDATED,
    PipelineState.CLOSED: EventType.PIPELINE_STAGE_COMPLETED,
}


def _get_db_session():
    from database.db import SessionLocal
    return SessionLocal()


def _state_history_from_db(pipeline_id: str) -> list[dict[str, Any]]:
    """Load and parse state_history for a pipeline from DB."""
    session = _get_db_session()
    try:
        from database.models import PipelineRun
        record = session.query(PipelineRun).filter(
            PipelineRun.correlation_id == pipeline_id
        ).first()
        if record and record.state_history:
            raw = json.loads(record.state_history)
            return raw if isinstance(raw, list) else []
        return []
    except Exception as exc:
        logger.warning("[COORD] Failed to load state_history for %s: %s", pipeline_id[:8], exc)
        return []
    finally:
        session.close()


class CoordinatorAgent(BaseAgent):
    """Orchestrates the full bug bounty pipeline with DB persistence.

    - Receives pipeline start requests via event bus
    - Sequences stages through the 11-state state machine
    - Persists pipeline state to SQLite (PipelineRun model)
    - Validates every transition against the formal state machine
    - Computes quality scores from transition history
    - Retries failed stages with exponential backoff
    """

    def __init__(self, max_retries: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.max_retries = max_retries
        self._active_pipelines: dict[str, dict[str, Any]] = {}
        self._agent_health: dict[str, dict[str, Any]] = {}

    def _get_agent_id(self) -> AgentId:
        return AgentId.COORDINATOR

    def _get_name(self) -> str:
        return "Coordinador"

    def _get_capabilities(self) -> list[str]:
        return [
            "orchestrate_pipeline",
            "resolve_conflicts",
            "retry_failed_stages",
            "quality_scoring",
            "persist_state",
        ]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [
            EventType.PIPELINE_START,
            EventType.PIPELINE_STAGE_COMPLETED,
            EventType.PIPELINE_FAILED,
            EventType.PIPELINE_CANCELLED,
            EventType.AGENT_HEALTH_CHANGED,
            EventType.AGENT_REGISTERED,
            EventType.SYSTEM_ERROR,
            EventType.STRATEGY_RECOMMENDATION,
            EventType.FINANCIAL_UPDATED,
            EventType.SUBMISSION_REQUESTED,
        ]

    def handle_event(self, event: AgentEvent) -> None:
        handler_map = {
            EventType.PIPELINE_START: self._on_pipeline_start,
            EventType.PIPELINE_STAGE_COMPLETED: self._on_stage_completed,
            EventType.PIPELINE_FAILED: self._on_pipeline_failed,
            EventType.PIPELINE_CANCELLED: self._on_pipeline_cancelled,
            EventType.AGENT_HEALTH_CHANGED: self._on_agent_health,
            EventType.AGENT_REGISTERED: self._on_agent_registered,
            EventType.SYSTEM_ERROR: self._on_system_error,
            EventType.STRATEGY_RECOMMENDATION: self._on_strategy,
            EventType.FINANCIAL_UPDATED: self._on_financial_update,
            EventType.SUBMISSION_REQUESTED: self._on_submission_requested,
        }
        handler = handler_map.get(event.event_type)
        if handler:
            handler(event)

    # ── Persistence ────────────────────────────────────────────────

    def _save_pipeline(self, pipeline_id: str, data: dict[str, Any]) -> None:
        """Upsert pipeline record to DB."""
        session = _get_db_session()
        try:
            from database.models import PipelineRun
            record = session.query(PipelineRun).filter(
                PipelineRun.correlation_id == pipeline_id
            ).first()
            if record:
                record.current_state = data.get("state", record.current_state)
                record.state_history = json.dumps(data.get("stages", []))
                record.quality_score = data.get("quality_score", record.quality_score)
                record.retry_count = data.get("retries", record.retry_count)
                record.error_message = data.get("error", record.error_message)
                if "completed_at" in data:
                    record.completed_at = data["completed_at"]
            else:
                record = PipelineRun(
                    target_id=data.get("target_id", 0),
                    correlation_id=pipeline_id,
                    current_state=data.get("state", "pending"),
                    state_history=json.dumps(data.get("stages", [])),
                    quality_score=data.get("quality_score", 0.0),
                    retry_count=data.get("retries", 0),
                    max_retries=self.max_retries,
                    error_message=data.get("error"),
                )
                session.add(record)
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("[COORD] Failed to persist pipeline %s: %s", pipeline_id[:8], exc)
        finally:
            session.close()

    def _load_pipeline(self, pipeline_id: str) -> dict[str, Any] | None:
        """Load pipeline from DB into active cache."""
        session = _get_db_session()
        try:
            from database.models import PipelineRun
            record = session.query(PipelineRun).filter(
                PipelineRun.correlation_id == pipeline_id
            ).first()
            if record:
                return {
                    "target_id": record.target_id,
                    "state": record.current_state,
                    "retries": record.retry_count,
                    "quality_score": record.quality_score or 0.0,
                    "stages": json.loads(record.state_history) if record.state_history else [],
                    "error": record.error_message or "",
                    "created_at": record.created_at.isoformat() if record.created_at else "",
                }
            return None
        except Exception as exc:
            logger.warning("[COORD] Failed to load pipeline %s: %s", pipeline_id[:8], exc)
            return None
        finally:
            session.close()

    # ── Pipeline lifecycle ─────────────────────────────────────────

    def _on_pipeline_start(self, event: AgentEvent) -> None:
        pipeline_id = event.correlation_id
        target_id = event.payload.get("target_id", 0)
        target_name = event.payload.get("target_name", "unknown")

        # ── Conflict resolution ────────────────────────────────────
        for pid, info in self._active_pipelines.items():
            existing_target = info.get("target_id")
            current_state = info.get("state", "")
            if existing_target == target_id and not is_terminal(current_state):
                logger.warning("[COORD] Conflict: target %s already has active pipeline %s",
                              target_name, pid[:8])
                self.emit(
                    EventType.SYSTEM_ALERT,
                    payload={
                        "type": "pipeline_conflict",
                        "message": f"Target {target_name} already has active pipeline {pid[:8]}",
                        "existing_pipeline": pid,
                        "new_pipeline": pipeline_id,
                    },
                    correlation_id=pipeline_id,
                )
                return

        logger.info("[COORD] Starting pipeline %s for target %s",
                    pipeline_id[:8], target_name)

        stages: list[dict[str, Any]] = [
            build_transition("", PipelineState.PENDING.value, "coordinator", "created",
                             {"target_name": target_name}),
        ]

        pipeline_data = {
            "target_id": target_id,
            "target_name": target_name,
            "state": PipelineState.PENDING.value,
            "retries": 0,
            "quality_score": 0.0,
            "stages": stages,
            "error": "",
        }

        self._active_pipelines[pipeline_id] = pipeline_data
        self._save_pipeline(pipeline_id, pipeline_data)

        self._advance_stage(pipeline_id, PipelineState.DISCOVERY, event)

    def _on_stage_completed(self, event: AgentEvent) -> None:
        pipeline_id = event.correlation_id
        completed_stage = event.payload.get("stage", "")
        next_stage_raw = event.payload.get("next_stage", "")

        info = self._active_pipelines.get(pipeline_id)
        if info is None:
            info = self._load_pipeline(pipeline_id)
            if info is None:
                logger.warning("[COORD] Stage completed for unknown pipeline %s", pipeline_id[:8])
                return
            self._active_pipelines[pipeline_id] = info

        # Find the completed state
        current_state = PipelineState.PENDING
        with contextlib.suppress(ValueError):
            current_state = PipelineState(completed_stage) if completed_stage else PipelineState(info.get("state", "pending"))

        # Record transition in history
        transition = build_transition(
            info.get("state", "pending"),
            completed_stage or info.get("state", "pending"),
            str(event.source),
            "completed",
            {"target_name": info.get("target_name", "")},
        )
        stages = info.setdefault("stages", [])
        stages.append(transition)

        # Determine next state
        next_state: PipelineState | None = None
        if next_stage_raw:
            with contextlib.suppress(ValueError):
                next_state = PipelineState(next_stage_raw)

        if next_state is None:
            next_state = next_stage(current_state)

        if next_state and validate_transition(current_state, next_state):
            info["state"] = next_state.value
            info["quality_score"] = compute_quality_score(stages)
            self._save_pipeline(pipeline_id, info)
            logger.info("[COORD] Pipeline %s: %s → %s (score=%.2f)",
                        pipeline_id[:8], current_state.value, next_state.value,
                        info["quality_score"])
            self._advance_stage(pipeline_id, next_state, event)
        else:
            # Pipeline complete
            info["state"] = PipelineState.CLOSED.value
            info["quality_score"] = compute_quality_score(stages)
            info["completed_at"] = datetime.now(timezone.utc)
            self._save_pipeline(pipeline_id, info)
            logger.info("[COORD] Pipeline %s completed (final score=%.2f)",
                        pipeline_id[:8], info["quality_score"])

    def _advance_stage(self, pipeline_id: str, state: PipelineState, trigger: AgentEvent) -> None:
        if is_terminal(state):
            logger.info("[COORD] Pipeline %s reached terminal state %s",
                        pipeline_id[:8], state.value)
            return

        # ── Mode check: stop at READY in manual mode ────────────────
        if state == PipelineState.READY and get_mode() == RastroMode.MANUAL:
            info = self._active_pipelines.get(pipeline_id)
            if info:
                info["state"] = PipelineState.READY.value
                info["quality_score"] = compute_quality_score(info.get("stages", []))
                self._save_pipeline(pipeline_id, info)
            self.emit(
                EventType.PIPELINE_STAGE_COMPLETED,
                payload={
                    **trigger.payload,
                    "stage": PipelineState.READY.value,
                    "pipeline_id": pipeline_id,
                    "manual_review_required": True,
                    "message": "Pipeline paused for manual review",
                },
                correlation_id=pipeline_id,
            )
            logger.info("[COORD] Pipeline %s paused at READY (manual mode)",
                        pipeline_id[:8])
            return

        # ── Mode check: auto-submit in automatic mode when READY ────
        if state == PipelineState.READY and get_mode() == RastroMode.AUTOMATIC:
            info = self._active_pipelines.get(pipeline_id)
            if info:
                info["state"] = PipelineState.READY.value
                info["quality_score"] = compute_quality_score(info.get("stages", []))
                self._save_pipeline(pipeline_id, info)
            self.emit(
                EventType.SUBMISSION_REQUESTED,
                payload={
                    **trigger.payload,
                    "stage": PipelineState.READY.value,
                    "next_stage": PipelineState.SUBMITTED.value,
                    "pipeline_id": pipeline_id,
                    "auto_submit": True,
                },
                target=AgentId.COORDINATOR,
                correlation_id=pipeline_id,
            )
            logger.info("[COORD] Pipeline %s auto-advancing to submission (auto mode)",
                        pipeline_id[:8])
            return

        target = STAGE_TO_AGENT.get(state)
        event_type = STAGE_TO_EVENT.get(state)

        if not target or not event_type:
            logger.warning("[COORD] No agent/event mapped for stage %s", state.value)
            return

        info = self._active_pipelines.get(pipeline_id)
        if info:
            info["state"] = state.value
            info["quality_score"] = compute_quality_score(info.get("stages", []))
            self._save_pipeline(pipeline_id, info)

        self.emit(
            event_type,
            payload={
                **trigger.payload,
                "stage": state.value,
                "pipeline_id": pipeline_id,
            },
            target=target,
            correlation_id=pipeline_id,
        )
        logger.info("[COORD] Advanced pipeline %s to stage %s → %s",
                    pipeline_id[:8], state.value, target.value)

    def _on_pipeline_failed(self, event: AgentEvent) -> None:
        pipeline_id = event.correlation_id
        error = event.payload.get("error", "unknown")
        logger.warning("[COORD] Pipeline %s failed: %s", pipeline_id[:8], error)

        info = self._active_pipelines.get(pipeline_id)
        if info is None:
            info = self._load_pipeline(pipeline_id)
            if info:
                self._active_pipelines[pipeline_id] = info

        if info:
            info["retries"] = info.get("retries", 0) + 1
            info["error"] = error

            # Record failure in history
            current_state_name = info.get("state", PipelineState.DISCOVERY.value)
            transition = build_transition(
                current_state_name, current_state_name,
                str(event.source), "failed",
                {"error": error},
            )
            info.setdefault("stages", []).append(transition)

            stages = info.get("stages", [])
            if can_retry(stages, self.max_retries):
                delay = get_retry_delay(info["retries"])
                logger.info("[COORD] Retrying pipeline %s (attempt %d/%d, delay=%ds)",
                            pipeline_id[:8], info["retries"], self.max_retries, delay)
                try:
                    current_state = PipelineState(current_state_name)
                except ValueError:
                    current_state = PipelineState.DISCOVERY
                info["state"] = current_state.value
                info["quality_score"] = compute_quality_score(stages)
                self._save_pipeline(pipeline_id, info)
                threading.Event().wait(delay)
                self._advance_stage(pipeline_id, current_state, event)
            else:
                logger.error("[COORD] Pipeline %s exhausted retries", pipeline_id[:8])
                info["state"] = PipelineState.FAILED.value
                info["quality_score"] = compute_quality_score(stages)
                info["completed_at"] = datetime.now(timezone.utc)
                self._save_pipeline(pipeline_id, info)

    def _on_pipeline_cancelled(self, event: AgentEvent) -> None:
        pipeline_id = event.correlation_id
        info = self._active_pipelines.get(pipeline_id)
        if info is None:
            return
        info["state"] = PipelineState.CANCELLED.value
        info["quality_score"] = compute_quality_score(info.get("stages", []))
        info["completed_at"] = datetime.now(timezone.utc)
        stages = info.setdefault("stages", [])
        stages.append(build_transition(
            info.get("state", ""), PipelineState.CANCELLED.value,
            str(event.source), "cancelled",
        ))
        self._save_pipeline(pipeline_id, info)
        logger.info("[COORD] Pipeline %s cancelled", pipeline_id[:8])

    def _on_agent_registered(self, event: AgentEvent) -> None:
        agent_id = event.payload.get("agent_id", "unknown")
        self._agent_health[agent_id] = {
            "status": "idle",
            "last_seen": event.timestamp,
            "capabilities": event.payload.get("capabilities", []),
        }
        logger.info("[COORD] Agent registered: %s", agent_id)

    def _on_agent_health(self, event: AgentEvent) -> None:
        agent_id = event.payload.get("agent_id", "unknown")
        status = event.payload.get("status", "unknown")
        if agent_id in self._agent_health:
            self._agent_health[agent_id].update({
                "status": status,
                "last_seen": event.timestamp,
            })

    def _on_system_error(self, event: AgentEvent) -> None:
        logger.warning("[COORD] System error from %s: %s",
                       event.source, event.payload.get("error", ""))

    def _on_strategy(self, event: AgentEvent) -> None:
        logger.info("[COORD] Strategy recommendation received",
                    extra={"payload": event.payload})

    def _on_financial_update(self, event: AgentEvent) -> None:
        pipeline_id = event.correlation_id
        info = self._active_pipelines.get(pipeline_id)
        if info is None:
            return
        current_state = info.get("state", "")
        if current_state == PipelineState.PAID.value:
            self._advance_stage(
                pipeline_id,
                PipelineState.PAID,
                AgentEvent(
                    event_type=EventType.PIPELINE_STAGE_COMPLETED,
                    source=AgentId.COORDINATOR,
                    target=AgentId.COORDINATOR,
                    correlation_id=pipeline_id,
                    payload={"stage": PipelineState.PAID.value, "next_stage": PipelineState.CLOSED.value},
                ),
            )

    def _on_submission_requested(self, event: AgentEvent) -> None:
        pipeline_id = event.correlation_id
        info = self._active_pipelines.get(pipeline_id)
        if info is None:
            logger.warning("[COORD] Submission requested for unknown pipeline %s", pipeline_id[:8])
            return

        # Global safety check
        if get_setting("rastro.never_submit_without_approval", True):
            logger.info("[COORD] Blocked auto-submit pipeline %s (approval required)", pipeline_id[:8])
            self.emit(
                EventType.SYSTEM_ALERT,
                payload={
                    "type": "submission_blocked",
                    "message": "Auto-submission blocked: 'Never submit without approval' is enabled",
                    "pipeline_id": pipeline_id,
                },
                correlation_id=pipeline_id,
            )
            return

        target_id = info.get("target_id")
        if not target_id:
            logger.warning("[COORD] No target_id for pipeline %s", pipeline_id[:8])
            return

        # Find the platform for this target
        session = _get_db_session()
        try:
            from database.models import Report, Target

            target = session.query(Target).filter(Target.id == target_id).first()
            if not target:
                logger.warning("[COORD] Target %s not found for submission", target_id)
                return

            platform = (target.domain or "unknown").split(".")[-2] if target.domain else "hackerone"
            platform_map = {"hackerone": "hackerone", "bugcrowd": "bugcrowd", "intigriti": "intigriti", "yeswehack": "yeswehack", "synack": "synack"}
            platform_id = platform_map.get(platform, "hackerone")

            report = session.query(Report).filter(
                Report.target == target.name
            ).order_by(Report.id.desc()).first()

            if not report:
                logger.warning("[COORD] No report found for target %s", target.name)
                return

            report_id = report.id
        except Exception as exc:
            logger.error("[COORD] Failed to lookup submission data: %s", exc)
            return
        finally:
            session.close()

        # Execute submission
        try:
            from core_engines.tracking.service import submit_report_to_platform

            result = submit_report_to_platform(report_id, platform_id)
            if result.get("success"):
                logger.info("[COORD] Pipeline %s submitted to %s (ext_id=%s)",
                            pipeline_id[:8], platform_id, result.get("external_id", ""))
                self._advance_stage(
                    pipeline_id,
                    PipelineState.READY,
                    AgentEvent(
                        event_type=EventType.PIPELINE_STAGE_COMPLETED,
                        source=AgentId.COORDINATOR,
                        target=AgentId.COORDINATOR,
                        correlation_id=pipeline_id,
                        payload={"stage": PipelineState.READY.value, "next_stage": PipelineState.SUBMITTED.value},
                    ),
                )
            else:
                logger.warning("[COORD] Submission failed for pipeline %s: %s",
                               pipeline_id[:8], result.get("error", "unknown"))
                self.emit(
                    EventType.PIPELINE_FAILED,
                    payload={"stage": PipelineState.SUBMITTED.value, "error": result.get("error", "submission_failed")},
                    correlation_id=pipeline_id,
                )
        except Exception as exc:
            logger.error("[COORD] Submission error for pipeline %s: %s", pipeline_id[:8], exc)
            self.emit(
                EventType.PIPELINE_FAILED,
                payload={"stage": PipelineState.SUBMITTED.value, "error": str(exc)},
                correlation_id=pipeline_id,
            )

    # ── Public API ─────────────────────────────────────────────────

    def get_pipeline_status(self, pipeline_id: str) -> dict[str, Any] | None:
        info = self._active_pipelines.get(pipeline_id)
        if info is None:
            info = self._load_pipeline(pipeline_id)
            if info:
                self._active_pipelines[pipeline_id] = info
        return info

    def list_pipelines(self) -> dict[str, Any]:
        # Load from DB as well
        session = _get_db_session()
        try:
            from database.models import PipelineRun
            records = session.query(PipelineRun).order_by(
                PipelineRun.created_at.desc()
            ).limit(50).all()
            for rec in records:
                pid = rec.correlation_id
                if pid not in self._active_pipelines:
                    self._active_pipelines[pid] = {
                        "target_id": rec.target_id,
                        "state": rec.current_state,
                        "retries": rec.retry_count,
                        "quality_score": rec.quality_score or 0.0,
                        "stages": json.loads(rec.state_history) if rec.state_history else [],
                        "error": rec.error_message or "",
                        "created_at": rec.created_at.isoformat() if rec.created_at else "",
                    }
        except Exception as exc:
            logger.warning("[COORD] Failed to load pipelines from DB: %s", exc)
        finally:
            session.close()
        return dict(self._active_pipelines)

    def get_agents_health(self) -> dict[str, Any]:
        return dict(self._agent_health)

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Remove a pipeline from both cache and DB."""
        self._active_pipelines.pop(pipeline_id, None)
        session = _get_db_session()
        try:
            from database.models import PipelineRun
            record = session.query(PipelineRun).filter(
                PipelineRun.correlation_id == pipeline_id
            ).first()
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        except Exception as exc:
            session.rollback()
            logger.error("[COORD] Failed to delete pipeline %s: %s", pipeline_id[:8], exc)
            return False
        finally:
            session.close()


_COORDINATOR: CoordinatorAgent | None = None


def get_coordinator() -> CoordinatorAgent:
    global _COORDINATOR
    if _COORDINATOR is None:
        _COORDINATOR = CoordinatorAgent()
    return _COORDINATOR
