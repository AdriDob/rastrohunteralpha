from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core_engines.agents.types import PipelineState

# Re-export the unified PipelineState
PipelineStage = PipelineState
STAGE_ORDER = [
    PipelineState.PENDING,
    PipelineState.DISCOVERY,
    PipelineState.VALIDATION,
    PipelineState.EVIDENCE,
    PipelineState.AI_REVIEW,
    PipelineState.READY,
    PipelineState.SUBMITTED,
    PipelineState.TRIAGED,
    PipelineState.PAID,
    PipelineState.CLOSED,
]


@dataclass
class PipelineContext:
    hot_path_id: str
    endpoint_id: int
    target_id: int
    stage: PipelineState = PipelineState.PENDING
    verdict_id: int | None = None
    finding_id: int | None = None
    report_id: int | None = None
    evidence_ids: list[int] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
