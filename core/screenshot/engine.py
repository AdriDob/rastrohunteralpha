"""
screenshot.engine — Screenshot Engine.

Visual evidence translation layer.
Converts pipeline outputs (Evidence, Verdicts, ROI, Attack Paths, Quick Wins)
into a structured visual representation for human review.

NOT a UI, NOT browser automation, NOT image generation.
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

LOG = logging.getLogger("rastro.screenshot")

BLOCK_TYPES = frozenset({
    "request", "response", "diff", "graph", "roi",
    "auth", "state_change", "contract_call",
})

HIGHLIGHT_LEVELS = frozenset({"low", "medium", "high", "critical"})

ANNOTATION_CATEGORIES = frozenset({
    "IDOR", "auth_bypass", "sensitive_fields", "cross_tenant_exposure",
    "financial_impact", "web3_state_changes", "contract_privilege_boundaries",
    "oracle_dependencies", "bridge_interactions",
})


# ── Data Classes ────────────────────────────────────────────────────


@dataclass
class VisualBlock:
    type: str
    content: str
    highlight_level: str = "low"

    def __post_init__(self) -> None:
        if self.type not in BLOCK_TYPES:
            LOG.warning("Unknown visual block type: %s", self.type)
        if self.highlight_level not in HIGHLIGHT_LEVELS:
            self.highlight_level = "low"


@dataclass
class AnnotationItem:
    category: str
    detail: str
    severity: str = "medium"

    def __post_init__(self) -> None:
        if self.category not in ANNOTATION_CATEGORIES:
            LOG.warning("Unknown annotation category: %s", self.category)
        if self.severity not in HIGHLIGHT_LEVELS:
            self.severity = "medium"


@dataclass
class ScreenshotSpec:
    title: str
    target: str
    endpoint: str
    vulnerability_type: str
    severity: str
    roi_score: float
    visual_blocks: List[VisualBlock] = field(default_factory=list)
    annotations: List[AnnotationItem] = field(default_factory=list)
    before_state: str = ""
    after_state: str = ""
    attack_path_summary: str = ""
    confidence: float = 0.0


@dataclass
class ScreenshotBundle:
    specs: List[ScreenshotSpec] = field(default_factory=list)
    summary: str = ""
    key_risks: List[str] = field(default_factory=list)
    roi_highlights: List[str] = field(default_factory=list)


# ── Engine ──────────────────────────────────────────────────────────


class ScreenshotEngine:
    """
    Translates pipeline evidence into structured visual representations.
    Does NOT execute scans, modify evidence, or generate findings.
    """

    def build(
        self,
        snapshot=None,
        evidence_graph=None,
        verdicts: Optional[List] = None,
        attack_surface=None,
        hot_paths: Optional[List] = None,
        roi_metadata: Optional[Dict[str, Any]] = None,
        quick_wins=None,
        target_name: str = "",
    ) -> ScreenshotBundle:
        LOG.info("Building ScreenshotBundle from pipeline outputs")

        # -- Extract data from available sources --
        endpoints = extract_endpoints(snapshot)
        hp_list = _extract_hot_paths_shared(snapshot, hot_paths)
        vd_map = _extract_verdict_map_shared(snapshot, verdicts, evidence_graph)
        comparisons = self._extract_comparisons(evidence_graph)
        surface_data = _extract_surface_shared(attack_surface, snapshot)
        qw_data = _extract_quick_wins_shared(quick_wins)

        # -- Build specs --
        specs: List[ScreenshotSpec] = self._build_specs_from_hot_paths(
            hp_list, endpoints, vd_map, comparisons, surface_data, qw_data, target_name,
        )

        if not specs:
            specs = self._build_specs_from_endpoints(
                endpoints, vd_map, comparisons, surface_data, qw_data, target_name,
            )

        if not specs:
            return ScreenshotBundle(summary="No evidence available to render")

        # -- Aggregate metadata --
        key_risks = self._aggregate_risks(specs, surface_data)
        roi_highlights = self._extract_roi_highlights(qw_data, specs, roi_metadata)
        summary = self._build_summary(specs, snapshot, target_name)

        return ScreenshotBundle(
            specs=specs,
            summary=summary,
            key_risks=key_risks,
            roi_highlights=roi_highlights,
        )

    # ── Data Extraction ─────────────────────────────────────────────

    @staticmethod
    def _extract_endpoints(snapshot) -> List[Dict[str, Any]]:
        if snapshot is None:
            return []
        raw = getattr(snapshot, "endpoints", [])
        out = []
        for ep in raw:
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
    def _extract_hot_paths(snapshot, hot_paths: Optional[List]) -> List[Dict[str, Any]]:
        out = []
        if hot_paths:
            for hp in hot_paths:
                if hasattr(hp, "nodes"):
                    out.append({
                        "nodes": list(getattr(hp, "nodes", [])),
                        "why_it_matters": getattr(hp, "why_it_matters", ""),
                        "estimated_reward": getattr(hp, "estimated_reward", "medium"),
                    })
                elif isinstance(hp, dict):
                    out.append(hp)
        if not out and snapshot is not None:
            raw = getattr(snapshot, "hot_paths", [])
            for hp in raw:
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
    def _extract_verdict_map(snapshot, verdicts: Optional[List], evidence_graph) -> Dict[str, Dict[str, Any]]:
        vd_map: Dict[str, Dict[str, Any]] = {}

        if verdicts:
            for v in verdicts:
                hot_path_id = getattr(v, "hot_path_id", "")
                vd_map[hot_path_id] = {
                    "hot_path_id": hot_path_id,
                    "status": getattr(v, "status", "unknown"),
                    "confidence": getattr(v, "confidence", 0.0),
                    "reproducibility_score": getattr(v, "reproducibility_score", 0.0),
                    "reason": getattr(v, "reason", ""),
                }

        if not vd_map and snapshot is not None:
            raw = getattr(snapshot, "verdicts", [])
            for v in raw:
                hpid = getattr(v, "hot_path_id", "")
                vd_map[hpid] = {
                    "hot_path_id": hpid,
                    "status": getattr(v, "status", "unknown"),
                    "confidence": getattr(v, "confidence", 0.0),
                    "reproducibility_score": getattr(v, "reproducibility_score", 0.0),
                }

        if not vd_map and evidence_graph is not None:
            for nd in evidence_graph.get_verdicts():
                hpid = nd.get("hot_path_id", "")
                vd_map[hpid] = {
                    "hot_path_id": hpid,
                    "status": nd.get("status", "unknown"),
                    "confidence": nd.get("confidence", 0.0),
                    "reproducibility_score": nd.get("reproducibility_score", 0.0),
                    "reason": nd.get("reason", ""),
                    "passed_rules": nd.get("passed_rules", []),
                    "failed_rules": nd.get("failed_rules", []),
                }

        return vd_map

    @staticmethod
    def _extract_comparisons(evidence_graph) -> List[Dict[str, Any]]:
        if evidence_graph is None:
            return []
        return evidence_graph.get_comparisons()

    @staticmethod
    def _extract_surface(attack_surface, snapshot) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {
            "idor_clusters": [],
            "auth_boundaries": [],
            "multi_tenant_zones": [],
            "graphql_surfaces": [],
        }

        if attack_surface is not None:
            if hasattr(attack_surface, "idor_clusters"):
                out["idor_clusters"] = list(attack_surface.idor_clusters)
            if hasattr(attack_surface, "auth_boundaries"):
                out["auth_boundaries"] = list(attack_surface.auth_boundaries)
            if hasattr(attack_surface, "multi_tenant_zones"):
                out["multi_tenant_zones"] = list(attack_surface.multi_tenant_zones)
            if hasattr(attack_surface, "graphql_surfaces"):
                out["graphql_surfaces"] = list(attack_surface.graphql_surfaces)

        if snapshot is not None:
            ss = getattr(snapshot, "attack_surface", None)
            if ss is not None:
                if not out["idor_clusters"]:
                    out["idor_clusters"] = list(getattr(ss, "idor_clusters", []))
                if not out["auth_boundaries"]:
                    out["auth_boundaries"] = list(getattr(ss, "auth_boundaries", []))
                if not out["multi_tenant_zones"]:
                    out["multi_tenant_zones"] = list(getattr(ss, "multi_tenant_zones", []))
                if not out["graphql_surfaces"]:
                    out["graphql_surfaces"] = list(getattr(ss, "graphql_surfaces", []))

        return out

    @staticmethod
    def _extract_quick_wins(quick_wins) -> Dict[str, Any]:
        if quick_wins is None:
            return {}
        out = {
            "top_quick_wins": [],
            "fast_exploit_paths": [],
            "low_effort_high_roi": [],
            "total_estimated_value": 0.0,
            "avg_quick_win_score": 0.0,
        }
        if hasattr(quick_wins, "top_quick_wins"):
            out["top_quick_wins"] = [
                {
                    "endpoint_path": getattr(w, "endpoint_path", ""),
                    "endpoint_method": getattr(w, "endpoint_method", ""),
                    "roi_score": getattr(w, "roi_score", 0.0),
                    "quick_win_score": getattr(w, "quick_win_score", 0.0),
                    "estimated_payout": getattr(w, "estimated_payout", 0.0),
                    "category": getattr(w, "category", ""),
                    "reasoning": getattr(w, "reasoning", ""),
                }
                for w in quick_wins.top_quick_wins
            ]
        if hasattr(quick_wins, "fast_exploit_paths"):
            out["fast_exploit_paths"] = [
                {
                    "entry_endpoint": getattr(p, "entry_endpoint", ""),
                    "vulnerability_type": getattr(p, "vulnerability_type", ""),
                    "chain_length": getattr(p, "chain_length", 0),
                }
                for p in quick_wins.fast_exploit_paths
            ]
        if hasattr(quick_wins, "low_effort_high_roi_targets"):
            out["low_effort_high_roi"] = [
                {
                    "endpoint_path": getattr(t, "endpoint_path", ""),
                    "roi_score": getattr(t, "roi_score", 0.0),
                }
                for t in quick_wins.low_effort_high_roi_targets
            ]
        if hasattr(quick_wins, "total_estimated_value"):
            out["total_estimated_value"] = quick_wins.total_estimated_value
        if hasattr(quick_wins, "avg_quick_win_score"):
            out["avg_quick_win_score"] = quick_wins.avg_quick_win_score
        return out

    # ── Spec Builders ───────────────────────────────────────────────

    def _build_specs_from_hot_paths(
        self,
        hot_paths: List[Dict[str, Any]],
        endpoints: List[Dict[str, Any]],
        verdict_map: Dict[str, Dict[str, Any]],
        comparisons: List[Dict[str, Any]],
        surface_data: Dict[str, List[Dict[str, Any]]],
        quick_wins: Dict[str, Any],
        target_name: str,
    ) -> List[ScreenshotSpec]:
        specs: List[ScreenshotSpec] = []
        seen: set = set()

        ep_by_path = {ep["path"]: ep for ep in endpoints if "path" in ep}

        for hp in hot_paths:
            nodes = hp.get("nodes", [hp.get("node_id", "")])
            path = hp.get("path", "")
            method = hp.get("method", "")
            risk_score = float(hp.get("risk_score", 0.0))
            vector = hp.get("vector", "")

            if not nodes and not path:
                continue

            # Determine the primary endpoint path from nodes
            primary_path = path
            primary_method = method
            for n in nodes:
                if ":" in n:
                    parts = n.split(":", 2)
                    if len(parts) >= 3:
                        primary_method = parts[1]
                        primary_path = parts[2]
                        break

            # Find matching verdict by hot path id or path
            vd = self._find_matching_verdict(hp, nodes, verdict_map, primary_path)
            # Find matching endpoint data
            ep_data = ep_by_path.get(primary_path, {})

            # Deduplicate by endpoint
            dedup_key = f"{primary_method}:{primary_path}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            vtype = self._derive_vulnerability_type(vector, ep_data)
            severity = self._derive_severity(risk_score)
            confidence = vd.get("confidence", 0.0) if vd else ep_data.get("confidence", 0.0)
            roi_score = self._find_roi_score(primary_path, quick_wins, ep_data)

            # Build visual blocks
            blocks = self._build_visual_blocks(
                primary_path, primary_method, vd, comparisons, ep_data, risk_score,
            )

            # Build annotations
            annotations = self._build_annotations(
                primary_path, vtype, ep_data, surface_data,
            )

            # Attack path summary
            attack_path_summary = self._build_attack_path_summary(hp, nodes)

            # Before/after state
            before_state, after_state = self._build_state_summary(vd, comparisons, primary_path)

            spec = ScreenshotSpec(
                title=f"{vtype} — {primary_method} {primary_path}",
                target=target_name,
                endpoint=f"{primary_method} {primary_path}",
                vulnerability_type=vtype,
                severity=severity,
                roi_score=roi_score,
                visual_blocks=blocks,
                annotations=annotations,
                before_state=before_state,
                after_state=after_state,
                attack_path_summary=attack_path_summary,
                confidence=confidence,
            )
            specs.append(spec)

        return specs

    def _build_specs_from_endpoints(
        self,
        endpoints: List[Dict[str, Any]],
        verdict_map: Dict[str, Dict[str, Any]],
        comparisons: List[Dict[str, Any]],
        surface_data: Dict[str, List[Dict[str, Any]]],
        quick_wins: Dict[str, Any],
        target_name: str,
    ) -> List[ScreenshotSpec]:
        specs: List[ScreenshotSpec] = []

        for ep in endpoints:
            path = ep.get("path", "/")
            method = ep.get("method", "GET")
            risk_score = float(ep.get("risk_score", 0.0))

            if risk_score < 15.0:
                continue

            vd = verdict_map.get(
                f"0:{path}",
                verdict_map.get(path, {}),
            )

            vtype = self._derive_vulnerability_type(ep.get("vector", ""), ep)
            severity = self._derive_severity(risk_score)
            confidence = vd.get("confidence", 0.0) if vd else ep.get("confidence", 0.0)
            roi_score = self._find_roi_score(path, quick_wins, ep)

            blocks = self._build_visual_blocks(
                path, method, vd, comparisons, ep, risk_score,
            )
            annotations = self._build_annotations(path, vtype, ep, surface_data)

            spec = ScreenshotSpec(
                title=f"{vtype} — {method} {path}",
                target=target_name,
                endpoint=f"{method} {path}",
                vulnerability_type=vtype,
                severity=severity,
                roi_score=roi_score,
                visual_blocks=blocks,
                annotations=annotations,
                confidence=confidence,
            )
            specs.append(spec)

        return specs

    # ── Visual Block Builder ────────────────────────────────────────

    @staticmethod
    def _build_visual_blocks(
        path: str,
        method: str,
        verdict: Optional[Dict[str, Any]],
        comparisons: List[Dict[str, Any]],
        ep_data: Dict[str, Any],
        risk_score: float,
    ) -> List[VisualBlock]:
        blocks: List[VisualBlock] = []

        # Request block
        req_content = f"{method} {path}"
        params = ep_data.get("params", {})
        if params:
            req_content += f"\nParams: {params}"
        blocks.append(VisualBlock(
            type="request",
            content=req_content,
            highlight_level=ScreenshotEngine._hl(risk_score, 40),
        ))

        # Response block — from evidence graph comparisons
        if comparisons:
            for comp in comparisons:
                comp_path = comp.get("hot_path_id", "")
                if path in comp_path:
                    baseline_status = comp.get("baseline_status", 0)
                    probe_status = comp.get("probe_status", 0)
                    sensitive_fields = comp.get("sensitive_fields", [])

                    resp_content = f"Baseline: {baseline_status} | Probe: {probe_status}"
                    if sensitive_fields:
                        resp_content += f"\nSensitive fields: {', '.join(sensitive_fields)}"
                    blocks.append(VisualBlock(
                        type="response",
                        content=resp_content,
                        highlight_level="critical" if sensitive_fields else "medium",
                    ))

                    # Diff block
                    diff_ratio = comp.get("body_diff_ratio", 0.0)
                    status_match = comp.get("status_match", True)
                    if diff_ratio > 0.0 or not status_match:
                        diff_content = f"Body diff: {diff_ratio:.1%}"
                        if not status_match:
                            diff_content += f" | Status: {baseline_status} -> {probe_status}"
                        blocks.append(VisualBlock(
                            type="diff",
                            content=diff_content,
                            highlight_level=ScreenshotEngine._hl(diff_ratio * 100, 30),
                        ))
                    break

        # Auth block
        labels = ep_data.get("labels", [])
        signals = ep_data.get("signals", [])
        is_auth_related = any("auth" in str(s).lower() for s in labels + signals)
        if is_auth_related or "auth" in path.lower():
            auth_content = "Auth context detected"
            if "auth_bypass" in signals or "authentication_surface" in labels:
                auth_content = "Auth bypass surface — possible authentication bypass"
            blocks.append(VisualBlock(
                type="auth",
                content=auth_content,
                highlight_level="high" if "bypass" in auth_content else "medium",
            ))

        # Web3 blocks
        if "web3" in signals or any("web3" in str(l) for l in labels):
            blocks.append(VisualBlock(
                type="contract_call",
                content="Web3 contract interaction detected",
                highlight_level="high",
            ))
            blocks.append(VisualBlock(
                type="state_change",
                content="State diff analysis available",
                highlight_level="medium",
            ))

        # ROI block
        if risk_score > 0:
            blocks.append(VisualBlock(
                type="roi",
                content=f"Risk score: {risk_score:.1f}",
                highlight_level=ScreenshotEngine._hl(risk_score, 50),
            ))

        return blocks

    # ── Annotation Builder ──────────────────────────────────────────

    @staticmethod
    def _build_annotations(
        path: str,
        vuln_type: str,
        ep_data: Dict[str, Any],
        surface_data: Dict[str, List[Dict[str, Any]]],
    ) -> List[AnnotationItem]:
        annotations: List[AnnotationItem] = []
        seen_categories: set = set()

        labels = ep_data.get("labels", [])
        signals = ep_data.get("signals", [])
        attack_surface = ep_data.get("attack_surface", [])
        potential_idor = ep_data.get("potential_idor", False)

        # IDOR annotation
        if vuln_type == "IDOR" or potential_idor:
            if "IDOR" not in seen_categories:
                annotations.append(AnnotationItem(
                    category="IDOR",
                    detail="Insecure Direct Object Reference — possible unauthorized data access",
                    severity="critical",
                ))
                seen_categories.add("IDOR")

        # Cross-tenant exposure
        if "multi_tenant" in labels or "cross_tenant" in attack_surface:
            if "cross_tenant_exposure" not in seen_categories:
                annotations.append(AnnotationItem(
                    category="cross_tenant_exposure",
                    detail="Multi-tenant boundary — possible cross-tenant data access (BOLA)",
                    severity="high",
                ))
                seen_categories.add("cross_tenant_exposure")

        # Auth bypass
        if "auth_bypass" in signals or "auth" in vuln_type.lower():
            if "auth_bypass" not in seen_categories:
                annotations.append(AnnotationItem(
                    category="auth_bypass",
                    detail="Authentication bypass surface detected",
                    severity="high",
                ))
                seen_categories.add("auth_bypass")

        # Sensitive fields
        if "sensitive" in labels or "data_exfiltration" in attack_surface:
            if "sensitive_fields" not in seen_categories:
                annotations.append(AnnotationItem(
                    category="sensitive_fields",
                    detail="Sensitive data exposure — PII, billing, or internal data",
                    severity="high",
                ))
                seen_categories.add("sensitive_fields")

        # Financial impact
        if "billing" in signals or "export" in signals:
            if "financial_impact" not in seen_categories:
                annotations.append(AnnotationItem(
                    category="financial_impact",
                    detail="Financial operation endpoint — possible monetary impact",
                    severity="critical",
                ))
                seen_categories.add("financial_impact")

        # Web3 annotations
        if "web3" in signals:
            if "web3_state_changes" not in seen_categories:
                annotations.append(AnnotationItem(
                    category="web3_state_changes",
                    detail="Web3 state change — contract state may be mutable",
                    severity="high",
                ))
                seen_categories.add("web3_state_changes")
            if "contract_privilege_boundaries" not in seen_categories:
                annotations.append(AnnotationItem(
                    category="contract_privilege_boundaries",
                    detail="Smart contract privilege boundary — possible access control vulnerability",
                    severity="critical",
                ))
                seen_categories.add("contract_privilege_boundaries")
            if "rpc" in str(signals).lower() or "oracle" in str(signals).lower():
                if "oracle_dependencies" not in seen_categories:
                    annotations.append(AnnotationItem(
                        category="oracle_dependencies",
                        detail="Oracle dependency — possible price manipulation or data feed attack",
                        severity="high",
                    ))
                    seen_categories.add("oracle_dependencies")
            if "bridge" in str(signals).lower() or "swap" in str(signals).lower():
                if "bridge_interactions" not in seen_categories:
                    annotations.append(AnnotationItem(
                        category="bridge_interactions",
                        detail="Bridge interaction — possible bridge exploit or signature replay",
                        severity="critical",
                    ))
                    seen_categories.add("bridge_interactions")

        # Surface-driven annotations
        for cluster_ep in surface_data.get("idor_clusters", []):
            cpath = cluster_ep.get("path", "") if isinstance(cluster_ep, dict) else ""
            if cpath and cpath in path:
                if "IDOR" not in seen_categories:
                    annotations.append(AnnotationItem(
                        category="IDOR",
                        detail="Endpoint in IDOR cluster — attack surface mapping",
                        severity="high",
                    ))
                    seen_categories.add("IDOR")

        return annotations

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _derive_vulnerability_type(vector: str, ep_data: Dict[str, Any]) -> str:
        if vector:
            return vector
        signals = ep_data.get("signals", [])
        labels = ep_data.get("labels", [])
        attack_surface = ep_data.get("attack_surface", [])
        if ep_data.get("potential_idor", False):
            return "IDOR"
        if "auth_bypass" in signals or "authentication_surface" in attack_surface:
            return "Auth Bypass"
        if "graphql" in labels:
            return "GraphQL Injection"
        if "web3" in signals:
            return "Web3 Vulnerability"
        if "file_operation" in labels:
            return "File Operation"
        if "admin" in labels or "admin_surface" in attack_surface:
            return "Privilege Escalation"
        if "ssrf" in signals:
            return "SSRF"
        if "business_logic" in labels:
            return "Business Logic"
        return "Security Finding"

    @staticmethod
    def _derive_severity(risk_score: float) -> str:
        if risk_score >= 80:
            return "critical"
        if risk_score >= 60:
            return "high"
        if risk_score >= 30:
            return "medium"
        return "low"

    @staticmethod
    def _hl(score: float, threshold_critical: float = 80) -> str:
        if score >= threshold_critical:
            return "critical"
        if score >= threshold_critical * 0.75:
            return "high"
        if score >= threshold_critical * 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _find_matching_verdict(
        hp: Dict[str, Any],
        nodes: List[str],
        verdict_map: Dict[str, Dict[str, Any]],
        primary_path: str,
    ) -> Optional[Dict[str, Any]]:
        # Try exact match by node_id
        for node in nodes:
            if node in verdict_map:
                return verdict_map[node]
        # Try by path suffix
        for k, v in verdict_map.items():
            if primary_path in k or k.endswith(primary_path):
                return v
        # Try hot_path_id
        hpid = hp.get("hot_path_id", hp.get("node_id", ""))
        if hpid in verdict_map:
            return verdict_map[hpid]
        return None

    @staticmethod
    def _find_roi_score(
        path: str,
        quick_wins: Dict[str, Any],
        ep_data: Dict[str, Any],
    ) -> float:
        for qw in quick_wins.get("top_quick_wins", []):
            if qw.get("endpoint_path", "") == path:
                return float(qw.get("roi_score", 0.0))
        return float(ep_data.get("risk_score", 0)) / 10.0

    @staticmethod
    def _build_attack_path_summary(hp: Dict[str, Any], nodes: List[str]) -> str:
        why = hp.get("why_it_matters", "")
        if why:
            return why
        reward = hp.get("estimated_reward", "medium")
        cluster_type = hp.get("cluster_type", "")
        parts = []
        if cluster_type:
            parts.append(f"Cluster: {cluster_type}")
        if nodes:
            parts.append(f"Path: {' -> '.join(nodes[:4])}")
        if reward:
            parts.append(f"Estimated reward: {reward}")
        return " | ".join(parts) if parts else ""

    @staticmethod
    def _build_state_summary(
        verdict: Optional[Dict[str, Any]],
        comparisons: List[Dict[str, Any]],
        path: str,
    ) -> tuple:
        if not comparisons:
            return "", ""
        for comp in comparisons:
            comp_path = comp.get("hot_path_id", "")
            if path in comp_path:
                before = f"Status: {comp.get('baseline_status', 'N/A')}, Hash: {comp.get('baseline_hash', '')[:12]}"
                after = f"Status: {comp.get('probe_status', 'N/A')}, Hash: {comp.get('probe_hash', '')[:12]}"
                if not comp.get("status_match", True):
                    after += " (status changed)"
                return before, after
        return "", ""

    # ── Aggregation ─────────────────────────────────────────────────

    @staticmethod
    def _aggregate_risks(
        specs: List[ScreenshotSpec],
        surface_data: Dict[str, List[Dict[str, Any]]],
    ) -> List[str]:
        risks: List[str] = []
        seen_risks: set = set()

        for spec in specs:
            if spec.severity == "critical":
                risk = f"[CRITICAL] {spec.endpoint} — {spec.vulnerability_type}"
                if risk not in seen_risks:
                    risks.append(risk)
                    seen_risks.add(risk)

        for spec in specs:
            if spec.severity == "high":
                risk = f"[HIGH] {spec.endpoint} — {spec.vulnerability_type}"
                if risk not in seen_risks:
                    risks.append(risk)
                    seen_risks.add(risk)

        # Surface-driven risks
        if surface_data.get("idor_clusters"):
            risks.append(f"[IDOR Cluster] {len(surface_data['idor_clusters'])} endpoints")
        if surface_data.get("auth_boundaries"):
            risks.append(f"[Auth Boundary] {len(surface_data['auth_boundaries'])} endpoints")
        if surface_data.get("multi_tenant_zones"):
            risks.append(f"[Multi-tenant] {len(surface_data['multi_tenant_zones'])} endpoints")

        return risks[:15]

    @staticmethod
    def _extract_roi_highlights(
        quick_wins: Dict[str, Any],
        specs: List[ScreenshotSpec],
        roi_metadata: Optional[Dict[str, Any]],
    ) -> List[str]:
        highlights: List[str] = []

        for qw in quick_wins.get("top_quick_wins", [])[:5]:
            path = qw.get("endpoint_path", "")
            score = qw.get("roi_score", 0.0)
            payout = qw.get("estimated_payout", 0.0)
            if score > 0:
                highlights.append(
                    f"ROI {score:.1f} — {qw.get('endpoint_method', '')} {path}"
                    + (f" (~${payout:.0f})" if payout else "")
                )

        for qw in quick_wins.get("low_effort_high_roi", [])[:3]:
            path = qw.get("endpoint_path", "")
            score = qw.get("roi_score", 0.0)
            if score > 0:
                highlights.append(
                    f"Low effort, high ROI — {path} (ROI {score:.1f})"
                )

        if not highlights:
            for spec in specs[:5]:
                if spec.roi_score > 0:
                    highlights.append(
                        f"ROI {spec.roi_score:.1f} — {spec.endpoint}"
                    )

        if roi_metadata:
            total = roi_metadata.get("total_estimated_value", 0)
            if total:
                highlights.append(f"Total estimated value: ${total:.0f}")

        return highlights[:10]

    @staticmethod
    def _build_summary(
        specs: List[ScreenshotSpec],
        snapshot,
        target_name: str,
    ) -> str:
        if not specs:
            return "No evidence available"

        total = len(specs)
        critical = sum(1 for s in specs if s.severity == "critical")
        high = sum(1 for s in specs if s.severity == "high")
        top_types = {}
        for s in specs:
            top_types[s.vulnerability_type] = top_types.get(s.vulnerability_type, 0) + 1
        top_vtype = max(top_types, key=top_types.get) if top_types else ""

        parts = [
            f"{total} finding{'s' if total != 1 else ''}",
        ]
        if critical:
            parts.append(f"{critical} critical")
        if high:
            parts.append(f"{high} high")
        if top_vtype:
            parts.append(f"top type: {top_vtype}")
        if target_name:
            parts.insert(0, f"Target: {target_name}")
        return " | ".join(parts)
