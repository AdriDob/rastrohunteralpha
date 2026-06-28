"""
core.artifacts — Canonical artifact objects for the system.

One Concept = One Canonical Object.
Every engine produces exactly one artifact type.
All consumers read from artifacts only.
"""

from core_engines.artifacts.ai_insights import (
    AIInsightArtifact,
)
from core_engines.artifacts.attack_surface import (
    AttackSurfaceArtifact,
)
from core_engines.artifacts.differential import (
    DifferentialArtifact,
)
from core_engines.artifacts.evidence import (
    EvidenceGraphArtifact,
)
from core_engines.artifacts.execution import (
    ExecutionPlanArtifact,
)
from core_engines.artifacts.hypothesis import (
    HypothesisArtifact,
)
from core_engines.artifacts.pipeline import (
    PipelineArtifact,
)
from core_engines.artifacts.quick_wins import (
    QuickWinsArtifact,
)
from core_engines.artifacts.roi import (
    ROIArtifact,
)
from core_engines.artifacts.screenshot import (
    ScreenshotArtifact,
)

__all__ = [
    "PipelineArtifact",
    "EvidenceGraphArtifact",
    "ScreenshotArtifact",
    "DifferentialArtifact",
    "QuickWinsArtifact",
    "ExecutionPlanArtifact",
    "AIInsightArtifact",
    "AttackSurfaceArtifact",
    "ROIArtifact",
    "HypothesisArtifact",
]
