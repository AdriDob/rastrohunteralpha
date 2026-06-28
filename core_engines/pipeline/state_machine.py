"""Formal pipeline state machine — validates transitions, tracks history, computes quality scores."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core_engines.agents.types import (  # noqa: F401
    PIPELINE_SEQUENCE,
    PIPELINE_TERMINAL,
    PipelineState,
    validate_transition,
)

logger = logging.getLogger("rastro.pipeline.state_machine")


STAGE_WEIGHTS: dict[PipelineState, float] = {
    PipelineState.PENDING: 0.0,
    PipelineState.DISCOVERY: 0.1,
    PipelineState.VALIDATION: 0.2,
    PipelineState.EVIDENCE: 0.3,
    PipelineState.AI_REVIEW: 0.5,
    PipelineState.READY: 0.6,
    PipelineState.SUBMITTED: 0.7,
    PipelineState.TRIAGED: 0.8,
    PipelineState.PAID: 0.9,
    PipelineState.CLOSED: 1.0,
    PipelineState.FAILED: 0.0,
    PipelineState.CANCELLED: 0.0,
}


def compute_progress(state: PipelineState) -> float:
    """Return 0.0–1.0 progress based on current state."""
    return STAGE_WEIGHTS.get(state, 0.0)


def compute_quality_score(state_history: list[dict[str, Any]]) -> float:
    """Compute a quality score (0.0–1.0) based on transition history.

    Factors:
    - Successfully completed stages
    - Absence of repeated failures
    - Smooth progression (no going backwards)
    """
    if not state_history:
        return 0.0

    success_count = 0
    fail_count = 0
    last_index = -1
    smooth = True

    for entry in state_history:
        target = entry.get("to_state", "")
        status = entry.get("status", "")

        if status == "failed":
            fail_count += 1
        elif status == "completed":
            success_count += 1

        try:
            idx = PIPELINE_SEQUENCE.index(PipelineState(target))
            if idx <= last_index:
                smooth = False
            last_index = idx
        except (ValueError, IndexError):
            logger.warning("Pipeline state not found in sequence", exc_info=True)

    total = success_count + fail_count
    if total == 0:
        return 0.0

    success_ratio = success_count / total
    smooth_bonus = 0.15 if smooth else 0.0
    fail_penalty = min(fail_count * 0.1, 0.5)

    return max(0.0, min(1.0, success_ratio * 0.85 + smooth_bonus - fail_penalty))


def build_transition(
    from_state: PipelineState | str,
    to_state: PipelineState | str,
    agent_id: str = "",
    status: str = "completed",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a timestamped transition entry for state_history."""
    if isinstance(from_state, PipelineState):
        from_state = from_state.value
    if isinstance(to_state, PipelineState):
        to_state = to_state.value
    return {
        "from_state": from_state,
        "to_state": to_state,
        "agent_id": agent_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }


def can_retry(state_history: list[dict[str, Any]], max_retries: int = 3) -> bool:
    """Check if retry is allowed based on history and max_retries."""
    fail_count = sum(1 for e in state_history if e.get("status") == "failed")
    return fail_count <= max_retries


def get_retry_delay(attempt: int) -> int:
    """Exponential backoff: 30s, 60s, 120s, 240s..."""
    return min(30 * (2 ** (attempt - 1)), 3600)


def next_stage(current: PipelineState) -> PipelineState | None:
    """Return the next sequential stage after current, or None if terminal."""
    try:
        idx = PIPELINE_SEQUENCE.index(current)
        if idx + 1 < len(PIPELINE_SEQUENCE):
            return PIPELINE_SEQUENCE[idx + 1]
        return None
    except ValueError:
        return None


def is_terminal(state: PipelineState | str) -> bool:
    """Check if the state is a terminal state."""
    if isinstance(state, str):
        try:
            state = PipelineState(state)
        except ValueError:
            return False
    return state in PIPELINE_TERMINAL
