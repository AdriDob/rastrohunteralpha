"""
QuickWinsArtifact — canonical quick wins representation.

Owned by: Quick Wins Engine
Dependencies: PipelineArtifact, EvidenceGraphArtifact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.contracts import Bundle


@dataclass
class QuickWinsArtifact(Bundle):
    report: Any = None
    total_opportunities: int = 0
    total_estimated_value: float = 0.0
    avg_quick_win_score: float = 0.0
    fastest_path_minutes: int = 0
    top_quick_wins: List[Dict[str, Any]] = field(default_factory=list)
    immediate_actions: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on("PipelineArtifact", "EvidenceGraphArtifact")
        if self.report is not None:
            self.total_opportunities = getattr(self.report, "total_opportunities", 0)
            self.total_estimated_value = getattr(self.report, "total_estimated_value", 0.0)
            self.avg_quick_win_score = getattr(self.report, "avg_quick_win_score", 0.0)
            self.fastest_path_minutes = getattr(self.report, "fastest_path_minutes", 0)
            top = getattr(self.report, "top_quick_wins", [])
            self.top_quick_wins = [
                {"path": getattr(w, "endpoint_path", ""), "method": getattr(w, "endpoint_method", ""), "score": getattr(w, "quick_win_score", 0.0), "roi": getattr(w, "roi_score", 0.0), "category": getattr(w, "category", "")}
                for w in top
            ]
            actions = getattr(self.report, "immediate_action_endpoints", [])
            self.immediate_actions = [
                {"path": getattr(a, "path", ""), "method": getattr(a, "method", ""), "action": getattr(a, "action", ""), "priority": getattr(a, "priority", "")}
                for a in actions
            ]

    def to_report(self):
        return self.report

    @classmethod
    def from_report(cls, report) -> "QuickWinsArtifact":
        return cls(report=report)
