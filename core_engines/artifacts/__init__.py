"""
core.artifacts — Canonical artifact objects for the system.

One Concept = One Canonical Object.
Every engine produces exactly one artifact type.
All consumers read from artifacts only.
"""

from core.artifacts.pipeline import (PipelineArtifact,)
from core.artifacts.evidence import (EvidenceGraphArtifact,)
from core.artifacts.screenshot import (ScreenshotArtifact,)
from core.artifacts.differential import (DifferentialArtifact,)
from core.artifacts.quick_wins import (QuickWinsArtifact,)
from core.artifacts.execution import (ExecutionPlanArtifact,)
from core.artifacts.ai_insights import (AIInsightArtifact,)
from core.artifacts.attack_surface import (AttackSurfaceArtifact,)
from core.artifacts.roi import (ROIArtifact,)
from core.artifacts.hypothesis import (HypothesisArtifact,)

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
