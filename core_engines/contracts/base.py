"""
core.contracts.base — Base artifact class and typing protocols.

All canonical bundles inherit from Artifact.
Protocols define expected interfaces for infrastructure components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


@dataclass
class Artifact:
    """
    Base class for all canonical artifacts.

    Every artifact in the system inherits from this, providing:
    - version: monotonic version counter for cache invalidation
    - timestamp: when this artifact was last computed
    - source_ids: identifiers of the input data that produced this artifact
    - dependencies: list of artifact type names this depends on
    - metadata: extensible key-value store for observability
    """
    version: int = 1
    timestamp: str = ""
    source_ids: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def bump(self) -> None:
        self.version += 1
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def depends_on(self, *artifact_types: str) -> None:
        for at in artifact_types:
            if at not in self.dependencies:
                self.dependencies.append(at)


@runtime_checkable
class ArtifactProtocol(Protocol):
    version: int
    timestamp: str
    source_ids: list[str]
    dependencies: list[str]
    metadata: dict[str, Any]


class Bundle(Artifact):
    """
    A Bundle is an Artifact that aggregates a set of related data.
    This is the canonical output of any engine component.
    """


@runtime_checkable
class DependencyGraphProtocol(Protocol):
    def get_dependencies(self, artifact_type: str) -> list[str]: ...
    def get_dependents(self, artifact_type: str) -> list[str]: ...
    def add_dependency(self, artifact_type: str, depends_on: str) -> None: ...
    def validate(self) -> bool: ...
    def execution_order(self) -> list[str]: ...


@runtime_checkable
class EventProtocol(Protocol):
    def emit(self, event_type: str, payload: Any) -> None: ...
    def subscribe(self, event_type: str, handler) -> None: ...
    def unsubscribe(self, event_type: str, handler) -> None: ...
    def get_events(self, event_type: str | None = None) -> list[dict[str, Any]]: ...


@runtime_checkable
class CacheProtocol(Protocol):
    def get(self, key: str) -> ArtifactProtocol | None: ...
    def set(self, key: str, artifact: ArtifactProtocol) -> None: ...
    def invalidate(self, key: str) -> None: ...
    def invalidate_many(self, keys: list[str]) -> None: ...
    def clear(self) -> None: ...
    def stats(self) -> dict[str, Any]: ...


@dataclass
class InvalidationPolicy:
    """Policy that determines when an artifact should be invalidated."""
    dependencies_changed: bool = False
    max_age_seconds: float | None = None
    force_recompute: bool = False
