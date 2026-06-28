"""
AttackSurfaceArtifact — canonical attack surface representation.

Owned by: AttackSurfaceMapper
Dependencies: PipelineArtifact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core_engines.contracts import Bundle


@dataclass
class AttackSurfaceArtifact(Bundle):
    idor_clusters: list[dict[str, Any]] = field(default_factory=list)
    auth_boundaries: list[dict[str, Any]] = field(default_factory=list)
    multi_tenant_zones: list[dict[str, Any]] = field(default_factory=list)
    graphql_surfaces: list[dict[str, Any]] = field(default_factory=list)
    technologies: list[dict[str, Any]] = field(default_factory=list)
    discovered_paths: list[str] = field(default_factory=list)
    total_surfaces: int = 0
    summary: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.depends_on("PipelineArtifact")
        self.total_surfaces = (
            len(self.idor_clusters) + len(self.auth_boundaries)
            + len(self.multi_tenant_zones) + len(self.graphql_surfaces)
        )

    @classmethod
    def from_surface_map(cls, surface_map) -> AttackSurfaceArtifact:
        return cls(
            idor_clusters=list(getattr(surface_map, "idor_clusters", [])),
            auth_boundaries=list(getattr(surface_map, "auth_boundaries", [])),
            multi_tenant_zones=list(getattr(surface_map, "multi_tenant_zones", [])),
            graphql_surfaces=list(getattr(surface_map, "graphql_surfaces", [])),
            technologies=list(getattr(surface_map, "technologies", [])),
            discovered_paths=list(getattr(surface_map, "discovered_paths", [])),
        )
