"""
intelligence.anti_drift — Anti-drift governance rules and enforcement.

Prevents architectural drift by enforcing ownership rules:
- Each artifact has exactly one owner (engine)
- No engine modifies another engine's output
- No engine keeps private copies of another engine's data
- AI Assistant is read-only consumer
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("rastro.intelligence.anti_drift")

# Canonical ownership matrix
# Each artifact is owned by exactly one engine
ARTIFACT_OWNERSHIP: Dict[str, str] = {
    "PipelineArtifact": "Pipeline",
    "AttackSurfaceArtifact": "AttackSurfaceMapper",
    "ROIArtifact": "ROI Engine",
    "HypothesisArtifact": "Hypothesis Engine",
    "EvidenceGraphArtifact": "Evidence Builder",
    "QuickWinsArtifact": "Quick Wins Engine",
    "ExecutionPlanArtifact": "Execution Hardening Layer",
    "ScreenshotArtifact": "Screenshot Engine",
    "DifferentialArtifact": "Differential Intelligence Engine",
    "AIInsightArtifact": "AI Assistant",
}

# Engines that are pure consumers (read-only, no write access to artifacts)
PURE_CONSUMERS: List[str] = [
    "AI Assistant",
    "Dashboard",
    "Report Engine",
]

# Read permissions: which engines can read which artifacts
READ_PERMISSIONS: Dict[str, List[str]] = {
    "Pipeline": ["PipelineArtifact"],
    "AttackSurfaceMapper": ["PipelineArtifact", "AttackSurfaceArtifact"],
    "ROI Engine": ["PipelineArtifact", "AttackSurfaceArtifact", "ROIArtifact"],
    "Hypothesis Engine": ["PipelineArtifact", "AttackSurfaceArtifact", "ROIArtifact", "HypothesisArtifact"],
    "Evidence Builder": ["PipelineArtifact", "EvidenceGraphArtifact"],
    "Quick Wins Engine": ["PipelineArtifact", "EvidenceGraphArtifact", "QuickWinsArtifact"],
    "Execution Hardening Layer": ["PipelineArtifact", "EvidenceGraphArtifact", "QuickWinsArtifact", "ExecutionPlanArtifact"],
    "Screenshot Engine": ["PipelineArtifact", "EvidenceGraphArtifact", "ScreenshotArtifact"],
    "Differential Intelligence Engine": [
        "PipelineArtifact", "EvidenceGraphArtifact", "ScreenshotArtifact",
        "DifferentialArtifact",
    ],
    "AI Assistant": [
        "PipelineArtifact", "EvidenceGraphArtifact", "ScreenshotArtifact",
        "DifferentialArtifact", "QuickWinsArtifact", "ExecutionPlanArtifact",
        "AttackSurfaceArtifact", "ROIArtifact", "HypothesisArtifact",
        "AIInsightArtifact",
    ],
    "Dashboard": [
        "PipelineArtifact", "ScreenshotArtifact", "DifferentialArtifact",
        "QuickWinsArtifact", "AIInsightArtifact", "ExecutionPlanArtifact",
    ],
    "Report Engine": ["PipelineArtifact", "EvidenceGraphArtifact"],
}


def get_owner(artifact_type: str) -> str:
    return ARTIFACT_OWNERSHIP.get(artifact_type, "unknown")


def can_read(engine_name: str, artifact_type: str) -> bool:
    perms = READ_PERMISSIONS.get(engine_name, [])
    return artifact_type in perms


def can_write(engine_name: str, artifact_type: str) -> bool:
    if engine_name in PURE_CONSUMERS:
        return False
    return ARTIFACT_OWNERSHIP.get(artifact_type) == engine_name


class AntiDriftEnforcer:
    """
    Enforces anti-drift rules at runtime.

    Logs violations but does not block execution (the system must continue running).
    """

    def __init__(self) -> None:
        self._violations: List[Dict[str, Any]] = []

    def check_write(
        self, engine_name: str, artifact_type: str, details: str = ""
    ) -> bool:
        """Check if an engine is allowed to write to an artifact."""
        if not can_write(engine_name, artifact_type):
            violation = {
                "type": "write_violation",
                "engine": engine_name,
                "artifact": artifact_type,
                "details": details,
                "owner": get_owner(artifact_type),
            }
            self._violations.append(violation)
            LOG.warning(
                "ANTI-DRIFT: %s attempted to write %s (owned by %s). %s",
                engine_name, artifact_type, get_owner(artifact_type), details,
            )
            return False
        return True

    def check_read(
        self, engine_name: str, artifact_type: str, details: str = ""
    ) -> bool:
        """Check if an engine is allowed to read an artifact."""
        if not can_read(engine_name, artifact_type):
            violation = {
                "type": "read_violation",
                "engine": engine_name,
                "artifact": artifact_type,
                "details": details,
            }
            self._violations.append(violation)
            LOG.warning(
                "ANTI-DRIFT: %s attempted to read %s (no permission). %s",
                engine_name, artifact_type, details,
            )
            return False
        return True

    def check_private_copy(
        self, engine_name: str, artifact_type: str, details: str = ""
    ) -> bool:
        """
        Check if an engine is keeping a private copy of another engine's data.
        This is a soft check — we log the warning but can't prevent it at runtime.
        """
        owner = get_owner(artifact_type)
        if owner != engine_name:
            violation = {
                "type": "private_copy",
                "engine": engine_name,
                "artifact": artifact_type,
                "owner": owner,
                "details": details,
            }
            self._violations.append(violation)
            LOG.warning(
                "ANTI-DRIFT: %s may be keeping private copy of %s (owned by %s). %s",
                engine_name, artifact_type, owner, details,
            )
            return False
        return True

    def get_violations(self) -> List[Dict[str, Any]]:
        return list(self._violations)

    def clear(self) -> None:
        self._violations.clear()

    def report(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        for v in self._violations:
            by_type[v["type"]] = by_type.get(v["type"], 0) + 1
        return {
            "total_violations": len(self._violations),
            "by_type": by_type,
            "violations": self._violations[-20:],
        }


_global_enforcer: Optional[AntiDriftEnforcer] = None


def get_enforcer() -> AntiDriftEnforcer:
    global _global_enforcer
    if _global_enforcer is None:
        _global_enforcer = AntiDriftEnforcer()
    return _global_enforcer
