"""
HypothesisArtifact — canonical hypothesis representation.

Owned by: Hypothesis Engine
Dependencies: PipelineArtifact, AttackSurfaceArtifact, ROIArtifact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.contracts import Bundle


@dataclass
class HypothesisArtifact(Bundle):
    total_hypotheses: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)
    avg_roi: float = 0.0
    max_roi: float = 0.0
    profitable_count: int = 0
    summary: str = ""
    queue_preview: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on("PipelineArtifact", "AttackSurfaceArtifact", "ROIArtifact")

    @classmethod
    def from_engine_output(cls, output) -> "HypothesisArtifact":
        return cls(
            total_hypotheses=getattr(output, "total_hypotheses", 0),
            by_source=dict(getattr(output, "by_source", {})),
            by_type=dict(getattr(output, "by_type", {})),
            avg_roi=getattr(output, "avg_roi", 0.0),
            max_roi=getattr(output, "max_roi", 0.0),
            profitable_count=getattr(output, "profitable_count", 0),
            summary=getattr(output, "summary", ""),
        )
