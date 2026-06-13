"""
DifferentialArtifact — canonical differential representation.

Owned by: Differential Intelligence Engine
Dependencies: PipelineArtifact, EvidenceGraphArtifact, ScreenshotArtifact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.contracts import Bundle


@dataclass
class DifferentialArtifact(Bundle):
    bundle: Any = None
    finding_count: int = 0
    anomaly_count: int = 0
    confidence: float = 0.0
    summary: str = ""
    categories: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on("PipelineArtifact", "EvidenceGraphArtifact", "ScreenshotArtifact")
        if self.bundle is not None:
            self.confidence = getattr(self.bundle, "confidence", 0.0)
            self.summary = getattr(self.bundle, "summary", "")
            self.anomaly_count = len(getattr(self.bundle, "interesting_anomalies", []))
            all_findings = []
            for field_name in (
                "target_differences", "endpoint_differences", "historical_changes",
                "cross_target_patterns", "web3_differences",
            ):
                items = getattr(self.bundle, field_name, [])
                all_findings.extend(items)
            self.finding_count = len(all_findings)
            cat: Dict[str, int] = {}
            for f in all_findings:
                c = getattr(f, "category", "general")
                cat[c] = cat.get(c, 0) + 1
            self.categories = cat

    def to_bundle(self):
        return self.bundle

    @classmethod
    def from_bundle(cls, bundle) -> "DifferentialArtifact":
        return cls(bundle=bundle)
