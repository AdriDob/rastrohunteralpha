"""
differential_intelligence_engine — Differential Intelligence Engine.

Detects interesting differences and anomalies across targets, endpoints,
versions, tenants, configurations, contracts, APIs, and behaviors.

NOT a scanner. NOT a finding generator. Does NOT modify evidence or scoring.

Outputs observations backed by existing data, never assertions of exploitation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.engine.extraction import (
    extract_endpoints,
    extract_hot_paths as _extract_hot_paths_shared,
    extract_verdict_map as _extract_verdict_map_shared,
    extract_surface as _extract_surface_shared,
    extract_quick_wins as _extract_quick_wins_shared,
)

LOG = logging.getLogger("rastro.differential_intelligence")

VALID_CATEGORIES = frozenset({
    "auth", "idor", "tenant", "graphql", "api", "admin", "export",
    "storage", "web3", "oracle", "bridge", "contract", "configuration",
    "historical", "general",
})

ENTITY_KEYWORDS: Dict[str, List[str]] = {
    "user": ["user", "profile", "member"],
    "account": ["account"],
    "organization": ["org", "organization", "company"],
    "team": ["team"],
    "project": ["project"],
    "workspace": ["workspace"],
    "file": ["file", "document", "upload", "attachment"],
    "billing": ["billing", "invoice", "payment"],
    "admin": ["admin", "dashboard", "management"],
    "auth": ["auth", "login", "token", "session", "oauth"],
    "export": ["export", "download", "report"],
    "web3": ["wallet", "contract", "tx", "transaction", "balance", "rpc", "web3"],
}


# ── Data Classes ────────────────────────────────────────────────────


@dataclass
class DifferentialFinding:
    title: str
    category: str
    description: str
    affected_objects: List[str] = field(default_factory=list)
    confidence: float = 0.0
    supporting_signals: List[str] = field(default_factory=list)
    risk_level: str = "low"
    requires_validation: bool = True
    novelty_score: float = 0.0
    confidence_score: float = 0.0
    potential_roi: float = 0.0
    validation_priority: str = "low"

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            LOG.warning("Unknown differential category: %s", self.category)


@dataclass
class DifferentialBundle:
    target_differences: List[DifferentialFinding] = field(default_factory=list)
    endpoint_differences: List[DifferentialFinding] = field(default_factory=list)
    historical_changes: List[DifferentialFinding] = field(default_factory=list)
    cross_target_patterns: List[DifferentialFinding] = field(default_factory=list)
    web3_differences: List[DifferentialFinding] = field(default_factory=list)
    interesting_anomalies: List[DifferentialFinding] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""


# ── Engine ──────────────────────────────────────────────────────────


class DifferentialIntelligenceEngine:
    """
    Analytical layer that detects interesting differences and anomalies.

    Consumes PipelineSnapshot, InvestigationGraph, EvidenceGraph,
    AttackSurfaceMap, ROI data, Hypotheses, Quick Wins, ScreenshotBundle,
    Verdicts, Evidence, historical snapshots, and cross-target memory.

    NEVER executes scans, modifies evidence, scoring, or findings.
    """

    def analyze(
        self,
        snapshot=None,
        investigation_graph=None,
        evidence_graph=None,
        attack_surface=None,
        roi_engine_output=None,
        hypothesis_output=None,
        quick_wins=None,
        screenshot_bundle=None,
        verdicts: Optional[List] = None,
        evidence_list: Optional[List] = None,
        historical_snapshots: Optional[List] = None,
        memory_pattern_library=None,
        target_name: str = "",
    ) -> DifferentialBundle:
        LOG.info("Running Differential Intelligence Engine")

        endpoints = extract_endpoints(snapshot)
        hp_list = _extract_hot_paths_shared(snapshot, investigation_graph=investigation_graph)
        vd_map = _extract_verdict_map_shared(snapshot, verdicts, evidence_graph)
        surface_data = _extract_surface_shared(attack_surface, snapshot)
        qw_data = _extract_quick_wins_shared(quick_wins)
        hypotheses = self._extract_hypotheses(hypothesis_output)
        sb_specs = self._extract_screenshot_specs(screenshot_bundle)
        roi_by_path = self._extract_roi(roi_engine_output, endpoints)

        target_diffs: List[DifferentialFinding] = []
        endpoint_diffs: List[DifferentialFinding] = []
        historical_diffs: List[DifferentialFinding] = []
        cross_target: List[DifferentialFinding] = []
        web3_diffs: List[DifferentialFinding] = []
        anomalies: List[DifferentialFinding] = []

        # 1. Target differential — comparing paths with shared entity types
        if endpoints:
            target_diffs = self._analyze_target_differences(
                endpoints, surface_data, qw_data,
            )

        # 2. Endpoint differential
        if endpoints:
            endpoint_diffs = self._analyze_endpoint_differences(
                endpoints, vd_map, surface_data, roi_by_path,
            )

        # 3. Historical differential
        if historical_snapshots:
            historical_diffs = self._analyze_historical_changes(
                snapshot, historical_snapshots,
            )

        # 4. Cross-target patterns
        if memory_pattern_library is not None and endpoints:
            cross_target = self._analyze_cross_target_patterns(
                endpoints, memory_pattern_library, target_name,
            )

        # 5. Web3 differential
        if endpoints or evidence_graph is not None:
            web3_diffs = self._analyze_web3_differences(
                endpoints, evidence_graph, snapshot,
            )

        # 6. Interesting anomalies — synthesis of noteworthy patterns
        all_findings = (
            target_diffs + endpoint_diffs + historical_diffs
            + cross_target + web3_diffs
        )
        anomalies = self._synthesize_anomalies(all_findings, hypotheses, sb_specs)

        confidence = self._compute_overall_confidence(all_findings)
        summary = self._build_summary(
            all_findings, anomalies, target_name, endpoints,
        )

        return DifferentialBundle(
            target_differences=target_diffs,
            endpoint_differences=endpoint_diffs,
            historical_changes=historical_diffs,
            cross_target_patterns=cross_target,
            web3_differences=web3_diffs,
            interesting_anomalies=anomalies,
            confidence=confidence,
            summary=summary,
        )

    # ── 1. Target Differential Analysis ─────────────────────────────

    @staticmethod
    def _analyze_target_differences(
        endpoints: List[Dict[str, Any]],
        surface_data: Dict[str, List[Dict[str, Any]]],
        qw_data: Dict[str, Any],
    ) -> List[DifferentialFinding]:
        findings: List[DifferentialFinding] = []
        seen: set = set()

        # Group endpoints by entity type
        by_entity: Dict[str, List[Dict[str, Any]]] = {}
        for ep in endpoints:
            path = ep.get("path", "/")
            entity = DifferentialIntelligenceEngine._detect_entity(path)
            if entity:
                by_entity.setdefault(entity, []).append(ep)

        # Compare auth patterns within entities
        for entity, eps in by_entity.items():
            if len(eps) < 2:
                continue
            auth_endpoints = [
                ep for ep in eps
                if any("auth" in str(s).lower() for s in ep.get("labels", []) + ep.get("signals", []))
            ]
            no_auth_endpoints = [
                ep for ep in eps
                if not any("auth" in str(s).lower() for s in ep.get("labels", []) + ep.get("signals", []))
            ]
            if auth_endpoints and no_auth_endpoints and len(no_auth_endpoints) >= 2:
                paths_no_auth = [f"{ep['method']} {ep['path']}" for ep in no_auth_endpoints[:3]]
                key = f"auth_gap:{entity}"
                if key not in seen:
                    seen.add(key)
                    findings.append(DifferentialFinding(
                        title=f"Auth gap in {entity} endpoints",
                        category="auth",
                        description=(
                            f"{len(no_auth_endpoints)} {entity} endpoints lack auth signals "
                            f"while {len(auth_endpoints)} have auth. This pattern may indicate "
                            f"inconsistent auth enforcement."
                        ),
                        affected_objects=paths_no_auth,
                        confidence=0.4,
                        supporting_signals=["auth_gap", f"entity:{entity}"],
                        risk_level="medium",
                        requires_validation=True,
                        novelty_score=0.6,
                        confidence_score=0.4,
                        validation_priority="medium",
                    ))

        # Missing surface coverage
        for entity, eps in by_entity.items():
            has_idor = any(ep.get("potential_idor", False) for ep in eps)
            total = len(eps)
            if total >= 5 and not has_idor:
                key = f"no_idor:{entity}"
                if key not in seen:
                    seen.add(key)
                    findings.append(DifferentialFinding(
                        title=f"Large {entity} surface with no IDOR signal",
                        category="idor",
                        description=(
                            f"{total} {entity} endpoints found but none flagged as potential IDOR. "
                            f"This may indicate incomplete coverage or a blind spot."
                        ),
                        affected_objects=[f"{entity} ({total} endpoints)"],
                        confidence=0.3,
                        supporting_signals=["no_idor_signal", f"entity:{entity}", "blind_spot"],
                        risk_level="low",
                        requires_validation=True,
                        novelty_score=0.5,
                        confidence_score=0.3,
                        validation_priority="low",
                    ))

        # Single auth boundary for entire target
        if surface_data.get("auth_boundaries"):
            paths = [str(e.get("path", "")) for e in surface_data["auth_boundaries"][:3]]
            if paths and "auth_boundary:single" not in seen:
                seen.add("auth_boundary:single")
                findings.append(DifferentialFinding(
                    title="Auth boundary detected",
                    category="auth",
                    description=(
                        f"{len(surface_data['auth_boundaries'])} endpoints form an auth boundary. "
                        f"Review for authentication enforcement consistency."
                    ),
                    affected_objects=paths,
                    confidence=0.5,
                    supporting_signals=["auth_boundary", "authentication_surface"],
                    risk_level="medium",
                    requires_validation=True,
                    novelty_score=0.4,
                    confidence_score=0.5,
                    validation_priority="low",
                ))

        # Multi-tenant presence
        if surface_data.get("multi_tenant_zones"):
            paths = [str(e.get("path", "")) for e in surface_data["multi_tenant_zones"][:3]]
            if paths and "multi_tenant" not in seen:
                seen.add("multi_tenant")
                findings.append(DifferentialFinding(
                    title="Multi-tenant zone — cross-tenant boundary risk",
                    category="tenant",
                    description=(
                        f"{len(surface_data['multi_tenant_zones'])} endpoints in multi-tenant zone. "
                        f"Cross-tenant access control should be verified."
                    ),
                    affected_objects=paths,
                    confidence=0.5,
                    supporting_signals=["multi_tenant", "tenant_boundary"],
                    risk_level="medium",
                    requires_validation=True,
                    novelty_score=0.5,
                    confidence_score=0.5,
                    validation_priority="medium",
                ))

        return findings

    # ── 2. Endpoint Differential Analysis ───────────────────────────

    @staticmethod
    def _analyze_endpoint_differences(
        endpoints: List[Dict[str, Any]],
        verdict_map: Dict[str, Dict[str, Any]],
        surface_data: Dict[str, List[Dict[str, Any]]],
        roi_by_path: Dict[str, float],
    ) -> List[DifferentialFinding]:
        findings: List[DifferentialFinding] = []
        seen: set = set()

        # Group by entity
        by_entity: Dict[str, List[Dict[str, Any]]] = {}
        for ep in endpoints:
            path = ep.get("path", "/")
            entity = DifferentialIntelligenceEngine._detect_entity(path)
            by_entity.setdefault(entity or "_none", []).append(ep)

        for entity, eps in by_entity.items():
            if len(eps) < 2:
                continue

            # Score range within entity
            scores = [float(ep.get("risk_score", 0)) for ep in eps]
            score_range = max(scores) - min(scores)
            if score_range >= 40:
                high = [ep for ep in eps if float(ep.get("risk_score", 0)) >= max(scores) - 10]
                low = [ep for ep in eps if float(ep.get("risk_score", 0)) <= min(scores) + 10]
                if high and low:
                    key_hi = f"score_gap:{entity}:{max(scores):.0f}"
                    if key_hi not in seen:
                        seen.add(key_hi)
                        findings.append(DifferentialFinding(
                            title=f"Risk score disparity in {entity} endpoints",
                            category="general",
                            description=(
                                f"{entity} endpoints show wide risk score range ({min(scores):.0f}-{max(scores):.0f}). "
                                f"High-scored endpoints may warrant deeper review."
                            ),
                            affected_objects=[f"{ep['method']} {ep['path']}" for ep in high[:2]],
                            confidence=0.5,
                            supporting_signals=[f"score_gap:{score_range:.0f}", f"entity:{entity}"],
                            risk_level="medium" if score_range >= 60 else "low",
                            requires_validation=True,
                            novelty_score=0.5,
                            confidence_score=0.5,
                            potential_roi=roi_by_path.get(high[0]["path"], 0) if high else 0,
                            validation_priority="medium" if score_range >= 60 else "low",
                        ))

            # Mixed auth patterns
            has_auth = any(
                "auth" in str(s).lower() for ep in eps
                for s in ep.get("labels", []) + ep.get("signals", [])
            )
            no_auth = [
                ep for ep in eps
                if not any("auth" in str(s).lower() for s in ep.get("labels", []) + ep.get("signals", []))
            ]
            if has_auth and no_auth:
                key_n = f"auth_mix:{entity}"
                if key_n not in seen:
                    seen.add(key_n)
                    findings.append(DifferentialFinding(
                        title=f"Inconsistent auth signals across {entity} endpoints",
                        category="auth",
                        description=(
                            f"{len(no_auth)}/{len(eps)} {entity} endpoints lack auth signals "
                            f"while others have them. This may indicate inconsistent auth enforcement."
                        ),
                        affected_objects=[f"{ep['method']} {ep['path']}" for ep in no_auth[:3]],
                        confidence=0.45,
                        supporting_signals=["auth_mix", f"entity:{entity}"],
                        risk_level="medium",
                        requires_validation=True,
                        novelty_score=0.6,
                        confidence_score=0.45,
                        validation_priority="medium",
                    ))

            # Hidden admin / export paths
            for keyword, cat in [("admin", "admin"), ("export", "export"), ("billing", "storage")]:
                matched = [ep for ep in eps if keyword in ep.get("path", "").lower()]
                if matched and keyword not in seen:
                    seen.add(f"{keyword}_path:{entity}")
                    findings.append(DifferentialFinding(
                        title=f"{keyword.title()} endpoints in {entity} surface",
                        category=cat,
                        description=(
                            f"{len(matched)} {keyword} endpoint{'' if len(matched) == 1 else 's'} "
                            f"found in {entity} context. Review access controls."
                        ),
                        affected_objects=[f"{ep['method']} {ep['path']}" for ep in matched[:3]],
                        confidence=0.5,
                        supporting_signals=[f"{keyword}_surface", f"entity:{entity}"],
                        risk_level="medium",
                        requires_validation=True,
                        novelty_score=0.4,
                        confidence_score=0.5,
                        validation_priority="low" if cat == "export" else "medium",
                    ))

        # GraphQL presence
        graphql_eps = [
            ep for ep in endpoints
            if "graphql" in ep.get("path", "").lower()
            or "graphql" in ep.get("labels", [])
        ]
        if graphql_eps:
            paths = [f"{ep['method']} {ep['path']}" for ep in graphql_eps[:3]]
            key = "graphql_presence"
            if key not in seen:
                seen.add(key)
                findings.append(DifferentialFinding(
                    title="GraphQL endpoint detected",
                    category="graphql",
                    description=(
                        f"{len(graphql_eps)} GraphQL entrie{'' if len(graphql_eps) == 1 else 's'} found. "
                        f"GraphQL surfaces may expose broader attack surface through nested queries."
                    ),
                    affected_objects=paths,
                    confidence=0.7,
                    supporting_signals=["graphql", "graphql_surface"],
                    risk_level="medium",
                    requires_validation=True,
                    novelty_score=0.4,
                    confidence_score=0.7,
                    validation_priority="low",
                ))

        return findings

    # ── 3. Historical Differential ──────────────────────────────────

    @staticmethod
    def _analyze_historical_changes(
        current_snapshot,
        historical_snapshots: List[Any],
    ) -> List[DifferentialFinding]:
        findings: List[DifferentialFinding] = []
        seen: set = set()

        current_eps = {
            f"{getattr(ep, 'method', 'GET')}:{getattr(ep, 'path', '/')}": ep
            for ep in getattr(current_snapshot, "endpoints", [])
        } if current_snapshot else {}

        if not current_eps or not historical_snapshots:
            return findings

        # Compare with most recent historical snapshot
        prev = historical_snapshots[-1]
        prev_eps = {
            f"{getattr(ep, 'method', 'GET')}:{getattr(ep, 'path', '/')}": ep
            for ep in getattr(prev, "endpoints", [])
        }

        # New endpoints
        new_keys = set(current_eps.keys()) - set(prev_eps.keys())
        if new_keys:
            new_list = list(new_keys)[:10]
            key = "new_endpoints"
            if key not in seen:
                seen.add(key)
                findings.append(DifferentialFinding(
                    title="New endpoints detected since last snapshot",
                    category="historical",
                    description=(
                        f"{len(new_keys)} new endpoint{'' if len(new_keys) == 1 else 's'} appeared "
                        f"since the previous snapshot. Review for potential new attack surface."
                    ),
                    affected_objects=new_list,
                    confidence=0.8,
                    supporting_signals=["new_endpoint", "historical_change"],
                    risk_level="medium",
                    requires_validation=True,
                    novelty_score=0.7,
                    confidence_score=0.8,
                    validation_priority="medium",
                ))

        # Removed endpoints
        removed_keys = set(prev_eps.keys()) - set(current_eps.keys())
        if removed_keys:
            removed_list = list(removed_keys)[:10]
            key = "removed_endpoints"
            if key not in seen:
                seen.add(key)
                findings.append(DifferentialFinding(
                    title="Endpoints removed since last snapshot",
                    category="historical",
                    description=(
                        f"{len(removed_keys)} endpoint{'' if len(removed_keys) == 1 else 's'} "
                        f"no longer present. May indicate infrastructure changes or rotated surface."
                    ),
                    affected_objects=removed_list,
                    confidence=0.7,
                    supporting_signals=["removed_endpoint", "historical_change"],
                    risk_level="low",
                    requires_validation=True,
                    novelty_score=0.6,
                    confidence_score=0.7,
                    validation_priority="low",
                ))

        # Risk score changes
        risk_changes: List[str] = []
        for key in set(current_eps.keys()) & set(prev_eps.keys()):
            cur_score = getattr(current_eps[key], "risk_score", 0)
            prev_score = getattr(prev_eps[key], "risk_score", 0)
            diff = cur_score - prev_score
            if abs(diff) >= 20:
                risk_changes.append(f"{key}: {prev_score:.0f} -> {cur_score:.0f} ({'+' if diff > 0 else ''}{diff:.0f})")
        if risk_changes:
            key = "risk_changes"
            if key not in seen:
                seen.add(key)
                findings.append(DifferentialFinding(
                    title="Risk score changes detected",
                    category="historical",
                    description=(
                        f"{len(risk_changes)} endpoint{'' if len(risk_changes) == 1 else 's'} "
                        f"changed risk score by >=20 points since last snapshot."
                    ),
                    affected_objects=risk_changes[:5],
                    confidence=0.6,
                    supporting_signals=["risk_change", "historical_change"],
                    risk_level="medium",
                    requires_validation=True,
                    novelty_score=0.6,
                    confidence_score=0.6,
                    validation_priority="medium",
                ))

        # Additional historical snapshots for trend detection
        if len(historical_snapshots) >= 3:
            all_snapshots = list(historical_snapshots) + ([current_snapshot] if current_snapshot else [])
            endpoint_lifespan: Dict[str, int] = {}
            for snap in all_snapshots:
                for ep in getattr(snap, "endpoints", []):
                    key = f"{getattr(ep, 'method', 'GET')}:{getattr(ep, 'path', '/')}"
                    endpoint_lifespan[key] = endpoint_lifespan.get(key, 0) + 1

            stable = [
                k for k, v in endpoint_lifespan.items()
                if v == len(all_snapshots)
            ]
            if stable and len(stable) >= 10:
                skey = "stable_pattern"
                if skey not in seen:
                    seen.add(skey)
                    findings.append(DifferentialFinding(
                        title=f"Stable endpoint surface ({len(stable)} persistent endpoints)",
                        category="historical",
                        description=(
                            f"{len(stable)} endpoints persisted across all {len(all_snapshots)} snapshots. "
                            f"Stable surface may indicate core API that warrants thorough review."
                        ),
                        affected_objects=stable[:5],
                        confidence=0.9,
                        supporting_signals=["persistent_endpoints", "historical_stable"],
                        risk_level="low",
                        requires_validation=True,
                        novelty_score=0.3,
                        confidence_score=0.9,
                        validation_priority="low",
                    ))

        return findings

    # ── 4. Cross-Target Pattern Reuse ──────────────────────────────

    @staticmethod
    def _analyze_cross_target_patterns(
        endpoints: List[Dict[str, Any]],
        memory_pattern_library,
        current_target: str,
    ) -> List[DifferentialFinding]:
        findings: List[DifferentialFinding] = []
        seen_categories: set = set()

        if not hasattr(memory_pattern_library, "find_similar_endpoints"):
            return findings

        for ep in endpoints[:20]:
            path = ep.get("path", "/")
            entity = DifferentialIntelligenceEngine._detect_entity(path)
            auth_smells = [
                s for s in ep.get("signals", [])
                if "auth" in s.lower() or "idor" in s.lower()
            ]

            try:
                similar = memory_pattern_library.find_similar_endpoints(
                    endpoint_path=path,
                    entity_type=entity,
                    auth_smells=auth_smells,
                    current_target=current_target,
                )
            except Exception:
                continue

            if similar:
                for match in similar[:3]:
                    profile = match.get("profile", {})
                    target = profile.get("target", "unknown")
                    sim_score = match.get("similarity", 0)
                    category_key = f"cross_target:{entity}:{target}"
                    if category_key not in seen_categories and sim_score >= 2:
                        seen_categories.add(category_key)
                        findings.append(DifferentialFinding(
                            title=f"Cross-target pattern: {entity} endpoint reused in {target}",
                            category="general",
                            description=(
                                f"Endpoint pattern for '{path}' in '{current_target}' matches similar "
                                f"endpoint in target '{target}' (similarity: {sim_score}). "
                                f"This may indicate shared codebase or API framework."
                            ),
                            affected_objects=[path, profile.get("path", "unknown")],
                            confidence=min(0.3 + sim_score * 0.15, 0.7),
                            supporting_signals=["cross_target_pattern", f"similarity:{sim_score}", f"entity:{entity}"],
                            risk_level="low",
                            requires_validation=True,
                            novelty_score=0.7,
                            confidence_score=min(0.3 + sim_score * 0.15, 0.7),
                            validation_priority="low",
                        ))

        return findings

    # ── 5. Web3 Differential ────────────────────────────────────────

    @staticmethod
    def _analyze_web3_differences(
        endpoints: List[Dict[str, Any]],
        evidence_graph,
        snapshot,
    ) -> List[DifferentialFinding]:
        findings: List[DifferentialFinding] = []
        seen: set = set()

        web3_endpoints = [
            ep for ep in endpoints
            if "web3" in ep.get("signals", [])
            or any("web3" in str(l) for l in ep.get("labels", []))
            or "web3" in ep.get("path", "").lower()
        ]

        if not web3_endpoints:
            return findings

        # Web3 surface diversity
        rpc_count = sum(1 for ep in web3_endpoints if "rpc" in ep.get("path", "").lower())
        contract_count = sum(1 for ep in web3_endpoints if "contract" in ep.get("path", "").lower())
        wallet_count = sum(1 for ep in web3_endpoints if "wallet" in ep.get("path", "").lower())

        if rpc_count and (contract_count or wallet_count):
            key = "web3_diverse"
            if key not in seen:
                seen.add(key)
                findings.append(DifferentialFinding(
                    title="Web3 surface diversity (RPC + contracts)",
                    category="web3",
                    description=(
                        f"Target exposes both RPC ({rpc_count}) and contract ({contract_count}) endpoints. "
                        f"Diverse Web3 surface may indicate multiple interaction patterns."
                    ),
                    affected_objects=[f"RPC: {rpc_count}", f"Contracts: {contract_count}"],
                    confidence=0.6,
                    supporting_signals=["web3_diverse", "rpc_surface", "contract_surface"],
                    risk_level="medium",
                    requires_validation=True,
                    novelty_score=0.5,
                    confidence_score=0.6,
                    validation_priority="medium",
                ))

        if wallet_count:
            key = "web3_wallet"
            if key not in seen:
                seen.add(key)
                findings.append(DifferentialFinding(
                    title="Web3 wallet operations detected",
                    category="web3",
                    description=(
                        f"{wallet_count} wallet-related endpoint{'' if wallet_count == 1 else 's'} found. "
                        f"Review for signature validation and access controls."
                    ),
                    affected_objects=[ep["path"] for ep in web3_endpoints if "wallet" in ep["path"].lower()][:3],
                    confidence=0.5,
                    supporting_signals=["wallet_surface", "web3"],
                    risk_level="high",
                    requires_validation=True,
                    novelty_score=0.6,
                    confidence_score=0.5,
                    validation_priority="high",
                ))

        # Check for bridge patterns
        bridge_eps = [
            ep for ep in web3_endpoints
            if "bridge" in ep.get("path", "").lower()
            or "swap" in ep.get("path", "").lower()
        ]
        if bridge_eps:
            key = "web3_bridge"
            if key not in seen:
                seen.add(key)
                findings.append(DifferentialFinding(
                    title="Bridge / swap operations detected",
                    category="bridge",
                    description=(
                        f"{len(bridge_eps)} bridge/swap endpoint{'' if len(bridge_eps) == 1 else 's'} found. "
                        f"Bridge operations involve cross-chain value transfer and warrant thorough review."
                    ),
                    affected_objects=[ep["path"] for ep in bridge_eps[:3]],
                    confidence=0.5,
                    supporting_signals=["bridge_surface", "web3", "cross_chain"],
                    risk_level="high",
                    requires_validation=True,
                    novelty_score=0.7,
                    confidence_score=0.5,
                    validation_priority="high",
                ))

        # Check for oracle patterns
        oracle_eps = [
            ep for ep in web3_endpoints
            if "oracle" in ep.get("path", "").lower()
            or "price" in ep.get("path", "").lower()
        ]
        if oracle_eps:
            key = "web3_oracle"
            if key not in seen:
                seen.add(key)
                findings.append(DifferentialFinding(
                    title="Oracle / price feed endpoints detected",
                    category="oracle",
                    description=(
                        f"{len(oracle_eps)} oracle/price endpoint{'' if len(oracle_eps) == 1 else 's'} found. "
                        f"Oracle manipulation may affect contract state."
                    ),
                    affected_objects=[ep["path"] for ep in oracle_eps[:3]],
                    confidence=0.5,
                    supporting_signals=["oracle_surface", "web3", "price_feed"],
                    risk_level="high",
                    requires_validation=True,
                    novelty_score=0.7,
                    confidence_score=0.5,
                    validation_priority="high",
                ))

        return findings

    # ── 6. Anomaly Synthesis ────────────────────────────────────────

    @staticmethod
    def _synthesize_anomalies(
        all_findings: List[DifferentialFinding],
        hypotheses: List[Dict[str, Any]],
        screenshot_specs: List[Any],
    ) -> List[DifferentialFinding]:
        anomalies: List[DifferentialFinding] = []
        seen_titles: set = set()

        # High-novelty findings that haven't been validated
        high_novelty = [
            f for f in all_findings
            if f.novelty_score >= 0.6 and f.risk_level in ("medium", "high")
        ]
        for f in high_novelty[:5]:
            key = f"anomaly_novel:{f.title}"
            if key not in seen_titles:
                seen_titles.add(key)
                anomalies.append(DifferentialFinding(
                    title=f"Anomaly: {f.title}",
                    category=f.category,
                    description=(
                        f"{f.description} This finding has high novelty ({f.novelty_score:.1f}) "
                        f"and moderate confidence ({f.confidence_score:.1f}) — review recommended."
                    ),
                    affected_objects=f.affected_objects,
                    confidence=f.confidence,
                    supporting_signals=f.supporting_signals + ["high_novelty"],
                    risk_level=f.risk_level,
                    requires_validation=True,
                    novelty_score=f.novelty_score,
                    confidence_score=f.confidence_score,
                    potential_roi=f.potential_roi,
                    validation_priority=f.validation_priority,
                ))

        # Hypothesis-driven anomalies: hypotheses not yet validated
        if hypotheses:
            unvalidated = [
                h for h in hypotheses
                if h.get("priority_score", 0) >= 70
            ]
            if unvalidated:
                total_hv = len(unvalidated)
                avg_roi = sum(h.get("roi_score", 0) for h in unvalidated) / max(total_hv, 1)
                key = "anomaly_high_value_hypotheses"
                if key not in seen_titles:
                    seen_titles.add(key)
                    types = list({
                        h.get("vulnerability_type", "unknown")
                        for h in unvalidated[:10]
                    })
                    anomalies.append(DifferentialFinding(
                        title=f"{total_hv} high-priority hypotheses pending validation",
                        category="general",
                        description=(
                            f"{total_hv} hypotheses scored >=70 priority remain unvalidated "
                            f"(avg ROI: {avg_roi:.1f}). Types: {', '.join(types[:5])}."
                        ),
                        affected_objects=[h.get("id", "") for h in unvalidated[:5]],
                        confidence=0.7,
                        supporting_signals=["pending_validation", "high_priority_hypothesis", "unvalidated"],
                        risk_level="medium",
                        requires_validation=True,
                        novelty_score=0.5,
                        confidence_score=0.7,
                        potential_roi=avg_roi,
                        validation_priority="high",
                    ))

        return anomalies

    # ── Data Extraction Helpers ─────────────────────────────────────

    @staticmethod
    def _extract_endpoints(snapshot) -> List[Dict[str, Any]]:
        if snapshot is None:
            return []
        out = []
        for ep in getattr(snapshot, "endpoints", []):
            out.append({
                "path": getattr(ep, "path", "/"),
                "method": getattr(ep, "method", "GET"),
                "risk_score": getattr(ep, "risk_score", 0.0),
                "confidence": getattr(ep, "confidence", 0.0),
                "labels": list(getattr(ep, "labels", [])),
                "attack_surface": list(getattr(ep, "attack_surface", [])),
                "signals": list(getattr(ep, "signals", [])),
                "vector": getattr(ep, "vector", ""),
                "potential_idor": getattr(ep, "potential_idor", False),
                "actionable": getattr(ep, "actionable", False),
            })
        return out

    @staticmethod
    def _extract_hot_paths(snapshot, investigation_graph) -> List[Dict[str, Any]]:
        out = []
        if investigation_graph is not None:
            for hp in getattr(investigation_graph, "hot_paths", []):
                out.append({
                    "nodes": list(getattr(hp, "nodes", [])),
                    "why_it_matters": getattr(hp, "why_it_matters", ""),
                    "estimated_reward": getattr(hp, "estimated_reward", "medium"),
                })
        if not out and snapshot is not None:
            for hp in getattr(snapshot, "hot_paths", []):
                out.append({
                    "node_id": getattr(hp, "node_id", ""),
                    "path": getattr(hp, "path", ""),
                    "method": getattr(hp, "method", "GET"),
                    "risk_score": getattr(hp, "risk_score", 0.0),
                    "vector": getattr(hp, "vector", ""),
                    "cluster_type": getattr(hp, "cluster_type", None),
                })
        return out

    @staticmethod
    def _extract_verdict_map(snapshot, verdicts, evidence_graph) -> Dict[str, Dict[str, Any]]:
        vd_map: Dict[str, Dict[str, Any]] = {}
        if verdicts:
            for v in verdicts:
                hpid = getattr(v, "hot_path_id", "")
                vd_map[hpid] = {
                    "status": getattr(v, "status", "unknown"),
                    "confidence": getattr(v, "confidence", 0.0),
                    "reason": getattr(v, "reason", ""),
                }
        if not vd_map and snapshot is not None:
            for v in getattr(snapshot, "verdicts", []):
                hpid = getattr(v, "hot_path_id", "")
                vd_map[hpid] = {
                    "status": getattr(v, "status", "unknown"),
                    "confidence": getattr(v, "confidence", 0.0),
                }
        if not vd_map and evidence_graph is not None:
            for nd in evidence_graph.get_verdicts():
                hpid = nd.get("hot_path_id", "")
                vd_map[hpid] = {
                    "status": nd.get("status", "unknown"),
                    "confidence": nd.get("confidence", 0.0),
                    "reason": nd.get("reason", ""),
                }
        return vd_map

    @staticmethod
    def _extract_surface(attack_surface, snapshot) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {
            "idor_clusters": [], "auth_boundaries": [],
            "multi_tenant_zones": [], "graphql_surfaces": [],
        }
        if attack_surface is not None:
            for attr in ("idor_clusters", "auth_boundaries", "multi_tenant_zones", "graphql_surfaces"):
                if hasattr(attack_surface, attr):
                    out[attr] = list(getattr(attack_surface, attr))
        if snapshot is not None:
            ss = getattr(snapshot, "attack_surface", None)
            if ss is not None:
                for attr in ("idor_clusters", "auth_boundaries", "multi_tenant_zones", "graphql_surfaces"):
                    if not out[attr]:
                        out[attr] = list(getattr(ss, attr, []))
        return out

    @staticmethod
    def _extract_quick_wins(quick_wins) -> Dict[str, Any]:
        if quick_wins is None:
            return {}
        out = {
            "top_quick_wins": [], "fast_exploit_paths": [],
            "low_effort_high_roi": [], "total_estimated_value": 0.0,
        }
        if hasattr(quick_wins, "top_quick_wins"):
            out["top_quick_wins"] = [
                {"endpoint_path": getattr(w, "endpoint_path", ""), "roi_score": getattr(w, "roi_score", 0.0)}
                for w in quick_wins.top_quick_wins
            ]
        if hasattr(quick_wins, "total_estimated_value"):
            out["total_estimated_value"] = quick_wins.total_estimated_value
        return out

    @staticmethod
    def _extract_hypotheses(hypothesis_output) -> List[Dict[str, Any]]:
        if hypothesis_output is None:
            return []
        queue = getattr(hypothesis_output, "attack_queue", None)
        if queue is None:
            return []
        out = []
        for h in queue.prioritized() if hasattr(queue, "prioritized") else queue:
            out.append({
                "id": getattr(h, "id", ""),
                "vulnerability_type": getattr(h, "vulnerability_type", "unknown"),
                "priority_score": getattr(h, "priority_score", 0.0),
                "roi_score": getattr(h, "roi_score", 0.0),
                "confidence": getattr(h, "confidence", 0.0),
            })
        return out

    @staticmethod
    def _extract_screenshot_specs(screenshot_bundle) -> List[Any]:
        if screenshot_bundle is None:
            return []
        return list(getattr(screenshot_bundle, "specs", []))

    @staticmethod
    def _extract_roi(roi_engine_output, endpoints) -> Dict[str, float]:
        roi_by_path: Dict[str, float] = {}
        for ep in endpoints:
            path = ep.get("path", "/")
            roi_by_path[path] = float(ep.get("risk_score", 0)) / 10.0
        if roi_engine_output is not None:
            if hasattr(roi_engine_output, "overall"):
                pass
        return roi_by_path

    # ── General Helpers ─────────────────────────────────────────────

    @staticmethod
    def _detect_entity(path: str) -> Optional[str]:
        lower = path.lower()
        for entity, keywords in ENTITY_KEYWORDS.items():
            for kw in keywords:
                if f"/{kw}" in lower or lower.startswith(f"{kw}/") or lower == kw:
                    return entity
        return None

    @staticmethod
    def _compute_overall_confidence(findings: List[DifferentialFinding]) -> float:
        if not findings:
            return 0.0
        return round(
            sum(f.confidence_score for f in findings) / len(findings), 2
        )

    @staticmethod
    def _build_summary(
        findings: List[DifferentialFinding],
        anomalies: List[DifferentialFinding],
        target_name: str,
        endpoints: List[Dict[str, Any]],
    ) -> str:
        if not findings and not anomalies:
            return "No differences detected"

        total = len(findings) + len(anomalies)
        by_cat: Dict[str, int] = {}
        for f in findings + anomalies:
            by_cat[f.category] = by_cat.get(f.category, 0) + 1
        top_cats = sorted(by_cat, key=by_cat.get, reverse=True)[:3]

        high_risk = sum(
            1 for f in findings + anomalies
            if f.risk_level in ("high", "critical")
        )

        parts = [
            f"Target: {target_name}" if target_name else "",
            f"{total} difference{'' if total == 1 else 's'} found",
            f"{high_risk} high-risk" if high_risk else "",
            f"top: {', '.join(top_cats)}" if top_cats else "",
            f"confidence: {DifferentialIntelligenceEngine._compute_overall_confidence(findings):.2f}",
        ]
        return " | ".join(p for p in parts if p)
