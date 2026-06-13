"""
ROIArtifact — canonical ROI representation.

Owned by: ROI Engine
Dependencies: PipelineArtifact, AttackSurfaceArtifact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.contracts import Bundle


@dataclass
class ROIArtifact(Bundle):
    endpoint_rois: Dict[str, float] = field(default_factory=dict)
    total_estimated_value: float = 0.0
    avg_roi_score: float = 0.0
    top_roi_endpoints: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on("PipelineArtifact", "AttackSurfaceArtifact")
