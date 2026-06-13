"""
ScreenshotArtifact — canonical visual representation.

Owned by: Screenshot Engine
Dependencies: PipelineArtifact, EvidenceGraphArtifact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.contracts import Bundle


@dataclass
class ScreenshotArtifact(Bundle):
    bundle: Any = None
    spec_count: int = 0
    summary: str = ""
    key_risks: List[str] = field(default_factory=list)
    roi_highlights: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on("PipelineArtifact", "EvidenceGraphArtifact")
        if self.bundle is not None:
            self.spec_count = len(getattr(self.bundle, "specs", []))
            self.summary = getattr(self.bundle, "summary", "")
            self.key_risks = list(getattr(self.bundle, "key_risks", []))
            self.roi_highlights = list(getattr(self.bundle, "roi_highlights", []))

    def to_bundle(self):
        return self.bundle

    @classmethod
    def from_bundle(cls, bundle) -> "ScreenshotArtifact":
        return cls(bundle=bundle)
