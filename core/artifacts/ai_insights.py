"""
AIInsightArtifact — canonical AI Assistant output.

Owned by: AI Assistant
Dependencies: PipelineArtifact, EvidenceGraphArtifact, ScreenshotArtifact,
             DifferentialArtifact, QuickWinsArtifact, ExecutionPlanArtifact

The AI Assistant is a pure consumer. It reads from all other artifacts
and produces narrative. It NEVER modifies other artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.contracts import Bundle


@dataclass
class AIInsightArtifact(Bundle):
    summary: str = ""
    narrative: str = ""
    recommendations: List[str] = field(default_factory=list)
    findings_explanation: str = ""
    differential_explanation: str = ""
    quick_wins_narrative: str = ""
    risk_narrative: str = ""
    source: str = "ai_assistant"

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on(
            "PipelineArtifact", "EvidenceGraphArtifact",
            "ScreenshotArtifact", "DifferentialArtifact",
            "QuickWinsArtifact", "ExecutionPlanArtifact",
        )
