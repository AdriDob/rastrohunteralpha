"""
EvidenceGraphArtifact — canonical wrapper around EvidenceGraph.

Owned by: Evidence Builder
Dependencies: PipelineArtifact
"""

from __future__ import annotations

from dataclasses import dataclass

from core_engines.contracts import Bundle
from core_engines.evidence.graph import EvidenceGraph as _EvidenceGraph


@dataclass
class EvidenceGraphArtifact(Bundle):
    graph: _EvidenceGraph | None = None
    verdict_count: int = 0
    comparison_count: int = 0
    confirmed_count: int = 0
    rejected_count: int = 0
    inconclusive_count: int = 0

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on("PipelineArtifact")
        if self.graph:
            verdicts = self.graph.get_verdicts()
            self.verdict_count = len(verdicts)
            self.comparison_count = len(self.graph.get_comparisons())
            self.confirmed_count = sum(
                1 for v in verdicts if v.get("status") == "confirmed"
            )
            self.rejected_count = sum(
                1 for v in verdicts if v.get("status") == "rejected"
            )
            self.inconclusive_count = sum(
                1 for v in verdicts if v.get("status") == "inconclusive"
            )

    def to_graph(self) -> _EvidenceGraph:
        if self.graph:
            return self.graph
        return _EvidenceGraph()

    @classmethod
    def from_graph(cls, graph: _EvidenceGraph) -> EvidenceGraphArtifact:
        return cls(graph=graph)
