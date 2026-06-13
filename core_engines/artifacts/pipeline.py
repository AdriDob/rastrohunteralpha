"""
PipelineArtifact — canonical wrapper around PipelineSnapshot.

Owned by: Pipeline
Dependencies: None (leaf input artifact)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.contracts import Bundle
from core_engines.engine.snapshot import (
    PipelineSnapshot as _PipelineSnapshot,
    EndpointSnapshot as _EndpointSnapshot,
    HotPathSnapshot as _HotPathSnapshot,
    VerdictSnapshot as _VerdictSnapshot,
    ReportSnapshot as _ReportSnapshot,
    AttackSurfaceSnapshot as _AttackSurfaceSnapshot,
    TargetSnapshot as _TargetSnapshot,
)


@dataclass
class PipelineArtifact(Bundle):
    snapshot: Optional[_PipelineSnapshot] = None
    status: str = "unknown"
    target_name: str = ""
    endpoint_count: int = 0
    hot_path_count: int = 0
    confirmed_count: int = 0
    coverage_score: float = 0.0
    summary: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on()
        if self.snapshot:
            self.status = self.snapshot.status
            target = getattr(self.snapshot, "target", None)
            if target:
                self.target_name = getattr(target, "name", "")
            self.endpoint_count = len(getattr(self.snapshot, "endpoints", []))
            self.hot_path_count = len(getattr(self.snapshot, "hot_paths", []))
            self.confirmed_count = len(getattr(self.snapshot, "verdicts", []))
            self.coverage_score = getattr(self.snapshot, "coverage_score", 0.0)
            self.summary = getattr(self.snapshot, "summary", "")

    def to_snapshot(self) -> _PipelineSnapshot:
        if self.snapshot:
            return self.snapshot
        raise ValueError("No snapshot available")

    @classmethod
    def from_snapshot(cls, snapshot: _PipelineSnapshot) -> "PipelineArtifact":
        return cls(snapshot=snapshot)
