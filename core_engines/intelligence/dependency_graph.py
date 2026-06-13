"""
intelligence.dependency_graph — Internal dependency graph for artifact relationships.

Defines the canonical execution order and dependency chain.
Every component knows only its direct dependencies.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from core_engines.contracts import DependencyGraphProtocol

LOG = logging.getLogger("rastro.intelligence.dependency_graph")

# Canonical dependency chain
# Each entry: (artifact_type, [list_of_dependencies])
CANONICAL_ORDER: List[str] = [
    "PipelineArtifact",
    "AttackSurfaceArtifact",
    "ROIArtifact",
    "HypothesisArtifact",
    "EvidenceGraphArtifact",
    "QuickWinsArtifact",
    "ExecutionPlanArtifact",
    "ScreenshotArtifact",
    "DifferentialArtifact",
    "AIInsightArtifact",
]

CANONICAL_DEPENDENCIES: Dict[str, List[str]] = {
    "PipelineArtifact": [],
    "AttackSurfaceArtifact": ["PipelineArtifact"],
    "ROIArtifact": ["PipelineArtifact", "AttackSurfaceArtifact"],
    "HypothesisArtifact": ["PipelineArtifact", "AttackSurfaceArtifact", "ROIArtifact"],
    "EvidenceGraphArtifact": ["PipelineArtifact"],
    "QuickWinsArtifact": ["PipelineArtifact", "EvidenceGraphArtifact"],
    "ExecutionPlanArtifact": ["PipelineArtifact", "EvidenceGraphArtifact", "QuickWinsArtifact"],
    "ScreenshotArtifact": ["PipelineArtifact", "EvidenceGraphArtifact"],
    "DifferentialArtifact": ["PipelineArtifact", "EvidenceGraphArtifact", "ScreenshotArtifact"],
    "AIInsightArtifact": [
        "PipelineArtifact", "EvidenceGraphArtifact",
        "ScreenshotArtifact", "DifferentialArtifact",
        "QuickWinsArtifact", "ExecutionPlanArtifact",
    ],
}


class DependencyGraph:
    """
    Directed acyclic graph of artifact dependencies.

    Ensures:
    - No circular dependencies
    - Every component knows only its direct dependencies
    - Execution order is deterministic
    """

    def __init__(self) -> None:
        self._dependencies: Dict[str, List[str]] = {}
        self._dependents: Dict[str, List[str]] = {}
        self._order: List[str] = []
        self._initialize()

    def _initialize(self) -> None:
        for artifact_type, deps in CANONICAL_DEPENDENCIES.items():
            self._dependencies[artifact_type] = list(deps)
            for dep in deps:
                if dep not in self._dependents:
                    self._dependents[dep] = []
                if artifact_type not in self._dependents[dep]:
                    self._dependents[dep].append(artifact_type)
        self._order = list(CANONICAL_ORDER)
        self._validate()

    def get_dependencies(self, artifact_type: str) -> List[str]:
        return list(self._dependencies.get(artifact_type, []))

    def get_dependents(self, artifact_type: str) -> List[str]:
        return list(self._dependents.get(artifact_type, []))

    def add_dependency(self, artifact_type: str, depends_on: str) -> None:
        if artifact_type not in self._dependencies:
            self._dependencies[artifact_type] = []
        if depends_on not in self._dependencies[artifact_type]:
            self._dependencies[artifact_type].append(depends_on)
        if artifact_type not in self._dependents:
            self._dependents[artifact_type] = []
        if artifact_type not in self._dependents.setdefault(depends_on, []):
            self._dependents[depends_on].append(artifact_type)
        self._validate()

    def validate(self) -> bool:
        return self._validate()

    def _validate(self) -> bool:
        visited: Set[str] = set()
        path: Set[str] = set()

        def _dfs(node: str) -> bool:
            if node in path:
                LOG.error("Circular dependency detected: %s", node)
                return False
            if node in visited:
                return True
            path.add(node)
            visited.add(node)
            for dep in self._dependencies.get(node, []):
                if not _dfs(dep):
                    return False
            path.remove(node)
            return True

        for node in self._dependencies:
            if not _dfs(node):
                return False
        return True

    def execution_order(self) -> List[str]:
        return list(self._order)

    def affected_by(self, changed_artifact: str) -> List[str]:
        """
        Returns all artifact types that are affected when changed_artifact is updated.
        Uses BFS through the dependency graph.
        """
        affected: List[str] = []
        queue = [changed_artifact]
        visited: Set[str] = {changed_artifact}
        while queue:
            current = queue.pop(0)
            for dependent in self._dependents.get(current, []):
                if dependent not in visited:
                    visited.add(dependent)
                    affected.append(dependent)
                    queue.append(dependent)
        return affected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependencies": dict(self._dependencies),
            "dependents": dict(self._dependents),
            "execution_order": list(self._order),
            "valid": self._validate(),
        }

    @staticmethod
    def validate_execution_order(order: List[str]) -> bool:
        seen: Set[str] = set()
        for artifact in order:
            deps = CANONICAL_DEPENDENCIES.get(artifact, [])
            for dep in deps:
                if dep not in seen:
                    LOG.error(
                        "Execution order violation: %s depends on %s but %s comes first",
                        artifact, dep, dep,
                    )
                    return False
            seen.add(artifact)
        return True
