"""
ExecutionPlanArtifact — canonical execution plan representation.

Owned by: Execution Hardening Layer / Gap Analyzer
Dependencies: PipelineArtifact, EvidenceGraphArtifact, QuickWinsArtifact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.contracts import Bundle


@dataclass
class ExecutionStep:
    action: str
    target: str
    method: str = "GET"
    priority: str = "medium"
    reason: str = ""
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ExecutionPlanArtifact(Bundle):
    steps: List[ExecutionStep] = field(default_factory=list)
    total_steps: int = 0
    coverage_score: float = 0.0
    uncovered_count: int = 0
    blind_spots: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on("PipelineArtifact", "EvidenceGraphArtifact", "QuickWinsArtifact")
        self.total_steps = len(self.steps)

    def add_step(self, step: ExecutionStep) -> None:
        self.steps.append(step)
        self.total_steps = len(self.steps)
        self.bump()
