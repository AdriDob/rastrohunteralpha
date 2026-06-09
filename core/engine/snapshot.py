"""
PipelineSnapshot — immutable intermediate format for all reporting.

All report consumers MUST consume PipelineSnapshot.
No recomputation of scores or classification is allowed downstream.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EndpointSnapshot:
    path: str
    method: str
    risk_score: float
    confidence: float
    labels: List[str] = field(default_factory=list)
    attack_surface: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    vector: str = ""
    actionable: bool = False
    potential_idor: bool = False


@dataclass(frozen=True)
class HotPathSnapshot:
    node_id: str
    path: str
    method: str
    risk_score: float
    vector: str
    cluster_type: Optional[str] = None


@dataclass(frozen=True)
class VerdictSnapshot:
    hot_path_id: str
    status: str
    confidence: float
    reproducibility_score: float


@dataclass(frozen=True)
class ReportSnapshot:
    title: str
    severity: str
    affected_endpoint: str
    attack_vector: str


@dataclass(frozen=True)
class NoiseReductionSnapshot:
    total_input: int
    discarded_count: int
    clean_count: int
    noise_ratio: float
    reasoning: Dict[str, List[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class AttackSurfaceSnapshot:
    idor_clusters: List[Dict[str, Any]] = field(default_factory=list)
    auth_boundaries: List[Dict[str, Any]] = field(default_factory=list)
    multi_tenant_zones: List[Dict[str, Any]] = field(default_factory=list)
    graphql_surfaces: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TargetSnapshot:
    target_id: int
    name: str
    domain: Optional[str] = None
    endpoint_count: int = 0
    risk_score: float = 0.0


@dataclass(frozen=True)
class PipelineSnapshot:
    """
    Immutable output of a full pipeline run.

    This is the ONLY format that reporting, dashboard, and export
    consumers should read. No recomputation allowed.
    """
    status: str
    target: Optional[TargetSnapshot] = None
    endpoints: List[EndpointSnapshot] = field(default_factory=list)
    hot_paths: List[HotPathSnapshot] = field(default_factory=list)
    verdicts: List[VerdictSnapshot] = field(default_factory=list)
    reports: List[ReportSnapshot] = field(default_factory=list)
    noise_reduction: Optional[NoiseReductionSnapshot] = None
    attack_surface: Optional[AttackSurfaceSnapshot] = None
    coverage_score: float = 0.0
    timestamp: Optional[str] = None
    summary: str = ""


def from_pipeline_output(pipeline_result: Dict[str, Any], target_info: Optional[Dict[str, Any]] = None) -> PipelineSnapshot:
    endpoints = [
        EndpointSnapshot(
            path=ep.get("path", "/"),
            method=ep.get("method", "GET"),
            risk_score=float(ep.get("risk_score", 0)),
            confidence=float(ep.get("confidence", 0)),
            labels=ep.get("labels", []),
            attack_surface=ep.get("attack_surface", []),
            signals=ep.get("signals", []),
            vector=ep.get("vector", ""),
            actionable=bool(ep.get("actionable", False)),
            potential_idor=bool(ep.get("potential_idor", False)),
        )
        for ep in pipeline_result.get("endpoints", pipeline_result.get("clean_endpoints", []))
    ]

    hot_paths = [
        HotPathSnapshot(
            node_id=hp.get("node_id", ""),
            path=hp.get("path", ""),
            method=hp.get("method", "GET"),
            risk_score=float(hp.get("risk_score", 0)),
            vector=hp.get("vector", ""),
            cluster_type=hp.get("cluster_type"),
        )
        for hp in pipeline_result.get("hot_paths", [])
    ]

    verdicts = [
        VerdictSnapshot(
            hot_path_id=vid,
            status=v.get("status", "unknown"),
            confidence=float(v.get("confidence", 0)),
            reproducibility_score=float(v.get("reproducibility_score", 0)),
        )
        for vid, v in pipeline_result.get("verdicts", {}).items()
    ]

    reports = [
        ReportSnapshot(
            title=r.get("title", ""),
            severity=r.get("severity", ""),
            affected_endpoint=r.get("endpoint", r.get("affected_endpoint", "")),
            attack_vector=r.get("attack_vector", ""),
        )
        for r in pipeline_result.get("reports", [])
    ]

    target = None
    if target_info:
        target = TargetSnapshot(
            target_id=int(target_info.get("id", 0)),
            name=target_info.get("name", ""),
            domain=target_info.get("domain"),
            endpoint_count=len(endpoints),
            risk_score=float(max(ep.risk_score for ep in endpoints)) if endpoints else 0.0,
        )

    from datetime import datetime, timezone
    return PipelineSnapshot(
        status=pipeline_result.get("status", "unknown"),
        target=target,
        endpoints=endpoints,
        hot_paths=hot_paths,
        verdicts=verdicts,
        reports=reports,
        noise_reduction=NoiseReductionSnapshot(
            total_input=pipeline_result.get("total_endpoints", 0),
            discarded_count=pipeline_result.get("total_endpoints", 0) - pipeline_result.get("clean_endpoints", 0),
            clean_count=pipeline_result.get("clean_endpoints", 0),
            noise_ratio=float(pipeline_result.get("noise_ratio", 0)),
            reasoning={},
        ) if "noise_ratio" in pipeline_result else None,
        coverage_score=float(pipeline_result.get("coverage_score", 0)),
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=pipeline_result.get("assistant_summary", pipeline_result.get("summary", "")),
    )
