from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class PipelineStage(str, Enum):
    PENDING = "pending"
    EVIDENCE_COLLECTED = "evidence_collected"
    VERDICT_ISSUED = "verdict_issued"
    FINDING_CREATED = "finding_created"
    REPORT_GENERATED = "report_generated"
    FAILED = "failed"


STAGE_ORDER = [
    PipelineStage.PENDING,
    PipelineStage.EVIDENCE_COLLECTED,
    PipelineStage.VERDICT_ISSUED,
    PipelineStage.FINDING_CREATED,
    PipelineStage.REPORT_GENERATED,
]


@dataclass
class PipelineContext:
    hot_path_id: str
    endpoint_id: int
    target_id: int
    stage: PipelineStage = PipelineStage.PENDING
    verdict_id: Optional[int] = None
    finding_id: Optional[int] = None
    report_id: Optional[int] = None
    evidence_ids: List[int] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.evidence_ids is None:
            self.evidence_ids = []
        if self.metadata is None:
            self.metadata = {}


def validate_transition(current: PipelineStage, target: PipelineStage) -> bool:
    if current == target:
        return True
    try:
        ci = STAGE_ORDER.index(current)
        ti = STAGE_ORDER.index(target)
        return ti == ci + 1
    except ValueError:
        return False
