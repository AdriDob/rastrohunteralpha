"""
hypothesis.engine — HypothesisEngine orchestrator.

Data flow:
  attack_surface (scored endpoints + clusters) → rule generators → memory refinement
  → LLM enrichment → attack queue (prioritized)

This sits between the scoring layer and the validation layer in the pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core_engines.engine.hypothesis.models import (
    AttackQueue,
    Hypothesis,
    HypothesisEngineOutput,
    HypothesisSource,
    VulnerabilityType,
)
from core_engines.engine.hypothesis.generators import generate_hypotheses
from core_engines.engine.hypothesis.scorer import score_hypothesis, reorder_attack_queue
from core_engines.engine.hypothesis.memory import HypothesisMemory
from core_engines.engine.hypothesis.llm import enrich_reasoning, detect_gaps, refine_priority

LOG = logging.getLogger("rastro.hypothesis")


class HypothesisEngine:
    def __init__(
        self,
        memory: Optional[HypothesisMemory] = None,
        ollama_host: str = "http://localhost:11434",
        llm_model: str = "qwen2.5-coder",
        enable_llm: bool = False,
    ):
        self.memory = memory or HypothesisMemory()
        self.ollama_host = ollama_host
        self.llm_model = llm_model
        self.enable_llm = enable_llm

    def run(
        self,
        target_id: int,
        target_name: str,
        endpoints: List[Dict[str, Any]],
        attack_surface_map: Optional[Dict[str, Any]] = None,
        clusters: Optional[List[Dict[str, Any]]] = None,
        hot_paths: Optional[List[Dict[str, Any]]] = None,
        risk_verdicts: Optional[Dict[int, Dict[str, Any]]] = None,
        nuclei_findings: Optional[List[Dict[str, Any]]] = None,
    ) -> HypothesisEngineOutput:
        LOG.info("HypothesisEngine.run: target=%s (%d endpoints)", target_name, len(endpoints))

        hypotheses = self._stage_1_generate(target_id, target_name, endpoints, nuclei_findings)
        LOG.info("Stage 1 (generate): %d hypotheses", len(hypotheses))

        hypotheses = self._stage_2_score(hypotheses)
        LOG.info("Stage 2 (score): %d hypotheses scored", len(hypotheses))

        hypotheses = self._stage_3_memory(hypotheses)
        LOG.info("Stage 3 (memory): %d hypotheses refined", len(hypotheses))

        hypotheses = self._stage_4_score(hypotheses)
        LOG.info("Stage 4 (re-score): %d hypotheses after memory", len(hypotheses))

        if self.enable_llm:
            hypotheses = self._stage_5_llm(hypotheses, endpoints)
            LOG.info("Stage 5 (LLM): %d hypotheses enriched", len(hypotheses))

            hypotheses = self._stage_4_score(hypotheses)
            LOG.info("Stage 5b (re-score): %d hypotheses after LLM", len(hypotheses))

        max_endpoint_id = max((ep.get("id", 0) for ep in endpoints), default=0)
        graph_hypotheses = self._generate_graph_hypotheses(
            target_id, target_name, clusters, hot_paths, endpoints, max_endpoint_id,
        )
        if graph_hypotheses:
            graph_hypotheses = self._stage_2_score(graph_hypotheses)
            hypotheses.extend(graph_hypotheses)
            LOG.info("Graph hypotheses: %d added", len(graph_hypotheses))

        hypotheses = reorder_attack_queue(hypotheses)
        queue = AttackQueue(hypotheses=hypotheses, target_id=target_id)

        by_source: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for h in hypotheses:
            by_source[h.source.value] = by_source.get(h.source.value, 0) + 1
            by_type[h.vulnerability_type.value] = by_type.get(h.vulnerability_type.value, 0) + 1

        summary = self._build_summary(queue)

        roi_values = [h.roi_score for h in hypotheses]
        profitable = sum(1 for h in hypotheses if h.roi_score > 50.0)
        total_roi_value = sum(h.roi_score for h in hypotheses) / max(len(hypotheses), 1)

        return HypothesisEngineOutput(
            attack_queue=queue,
            total_hypotheses=len(hypotheses),
            by_source=by_source,
            by_type=by_type,
            top_priority=queue.prioritized()[0] if hypotheses else None,
            summary=summary,
            total_roi_value=round(total_roi_value, 2),
            avg_roi=round(sum(roi_values) / max(len(roi_values), 1), 2),
            max_roi=round(max(roi_values), 2) if roi_values else 0.0,
            profitable_count=profitable,
        )

    def _stage_1_generate(
        self, target_id: int, target_name: str, endpoints: List[Dict[str, Any]],
        nuclei_findings: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Hypothesis]:
        return generate_hypotheses(endpoints, target_id, target_name, nuclei_findings=nuclei_findings)

    def _stage_2_score(self, hypotheses: List[Hypothesis]) -> List[Hypothesis]:
        scored = []
        for h in hypotheses:
            risk_score = float(h.endpoint.get("risk_score", 0))
            scored.append(score_hypothesis(h, risk_score))
        return scored

    def _stage_3_memory(self, hypotheses: List[Hypothesis]) -> List[Hypothesis]:
        return self.memory.refine(hypotheses)

    def _stage_4_score(self, hypotheses: List[Hypothesis]) -> List[Hypothesis]:
        return self._stage_2_score(hypotheses)

    def _stage_5_llm(
        self, hypotheses: List[Hypothesis], endpoints: List[Dict[str, Any]],
    ) -> List[Hypothesis]:
        enriched = enrich_reasoning(hypotheses, host=self.ollama_host, model=self.llm_model)
        gap_hypotheses = detect_gaps(endpoints, hypotheses, host=self.ollama_host, model=self.llm_model)
        if gap_hypotheses:
            LOG.info("LLM gap detection: %d missed vulnerability patterns found", len(gap_hypotheses))
        reorder_suggestion = refine_priority(enriched, host=self.ollama_host, model=self.llm_model)
        if reorder_suggestion:
            id_order = {hid: i for i, hid in enumerate(reorder_suggestion)}
            enriched.sort(key=lambda h: id_order.get(h.id, 999))
            LOG.info("LLM priority reorder applied for top-%d hypotheses", len(reorder_suggestion))
        return enriched

    def _generate_graph_hypotheses(
        self,
        target_id: int,
        target_name: str,
        clusters: Optional[List[Dict[str, Any]]],
        hot_paths: Optional[List[Dict[str, Any]]],
        endpoints: List[Dict[str, Any]],
        max_id: int,
    ) -> List[Hypothesis]:
        if not clusters and not hot_paths:
            return []

        hypotheses: List[Hypothesis] = []
        endpoint_map = {ep.get("id"): ep for ep in endpoints}

        if hot_paths:
            for i, hp in enumerate(hot_paths):
                nodes = hp.get("nodes", []) if isinstance(hp, dict) else []
                template = hp.get("template", "") if isinstance(hp, dict) else ""
                bridge = hp.get("bridge_entity", "") if isinstance(hp, dict) else ""
                reward = hp.get("reward", "medium") if isinstance(hp, dict) else "medium"
                if not nodes:
                    continue

                start_type = "idor"
                if "auth" in template.lower():
                    start_type = "auth_bypass"
                elif "tenant" in template.lower() or "multi" in template.lower():
                    start_type = "privilege_escalation"
                elif "graphql" in template.lower():
                    start_type = "graphql_introspection"
                elif "web3" in template.lower():
                    start_type = "web3_rpc_leak"
                elif "export" in template.lower() or "data" in template.lower():
                    start_type = "data_exposure"

                hyp_id = f"graph_hp_{i}_{target_id}"

                evidence = [f"Hot path: {template}"] if template else [f"Investigation path with {len(nodes)} nodes"]
                if bridge:
                    evidence.append(f"Bridge entity: {bridge}")

                hypotheses.append(Hypothesis(
                    id=hyp_id,
                    vulnerability_type=VulnerabilityType(start_type),
                    target_id=target_id,
                    target_name=target_name,
                    endpoint={},
                    likelihood=0.5,
                    impact=0.75 if reward == "high" else 0.55,
                    exploitability=0.5,
                    confidence=0.0,
                    priority_score=0.0,
                    evidence=evidence,
                    reasoning=template or f"Investigation path connecting {len(nodes)} endpoints — test for chained vulnerability.",
                    suggested_actions=[
                        f"Follow investigation path: {template}" if template else f"Test {len(nodes)} connected endpoints in sequence",
                        "Verify each endpoint's auth independently",
                        "Try cross-endpoint state manipulation",
                    ],
                    source=HypothesisSource.PATTERN,
                    vector="Chained",
                    attack_surface_labels=[],
                ))

        if clusters:
            for i, cluster in enumerate(clusters):
                name = cluster.get("name", "") if isinstance(cluster, dict) else ""
                endpoints_in_cluster = cluster.get("endpoints", []) if isinstance(cluster, dict) else []
                cluster_entities = cluster.get("entities", []) if isinstance(cluster, dict) else []
                if not name:
                    continue

                vt_map = {
                    "IDOR": VulnerabilityType.IDOR,
                    "Auth": VulnerabilityType.AUTH_BYPASS,
                    "Multi-tenant": VulnerabilityType.PRIVILEGE_ESCALATION,
                    "Data exposure": VulnerabilityType.DATA_EXPOSURE,
                    "GraphQL": VulnerabilityType.GRAPHQL_INTROSPECTION,
                    "Admin": VulnerabilityType.PRIVILEGE_ESCALATION,
                    "File operation": VulnerabilityType.FILE_OPERATION,
                    "Web3": VulnerabilityType.WEB3_RPC_LEAK,
                }
                vt = vt_map.get(name, VulnerabilityType.BUSINESS_LOGIC)

                ep_ids_seen = set()
                for cep in endpoints_in_cluster:
                    ep_id = cep.get("id") if isinstance(cep, dict) else None
                    if ep_id and ep_id not in ep_ids_seen and ep_id in endpoint_map:
                        ep_ids_seen.add(ep_id)

                if not ep_ids_seen:
                    continue

                hyp_id = f"cluster_{name.lower().replace(' ', '_')}_{target_id}"

                evidence = [f"Cluster: {name} ({len(endpoints_in_cluster)} endpoints)"]
                if cluster_entities:
                    evidence.append(f"Entities: {', '.join(cluster_entities)}")
                description = cluster.get("description", "") if isinstance(cluster, dict) else ""
                if description:
                    evidence.append(description)

                hypotheses.append(Hypothesis(
                    id=hyp_id,
                    vulnerability_type=vt,
                    target_id=target_id,
                    target_name=target_name,
                    endpoint={},
                    likelihood=0.65,
                    impact=0.75,
                    exploitability=0.6,
                    confidence=0.0,
                    priority_score=0.0,
                    evidence=evidence,
                    reasoning=f"Cluster '{name}' contains {len(endpoints_in_cluster)} related endpoints — test for cluster-wide vulnerability pattern.",
                    suggested_actions=[
                        f"Test all {len(endpoints_in_cluster)} endpoints in {name} cluster for {vt.value}",
                        "Verify each endpoint enforces authorization independently",
                        "Check for shared auth tokens or session patterns across cluster",
                    ],
                    source=HypothesisSource.PATTERN,
                    vector=name,
                    attack_surface_labels=[],
                ))

        return hypotheses

    def _build_summary(self, queue: AttackQueue) -> str:
        top = queue.top_k(5)
        if not top:
            return "No hypotheses generated for this target."
        lines = ["Hypothesis Engine Summary:"]
        for i, h in enumerate(top, 1):
            payout = h.score.breakdown.get("payout_estimate", 0)
            roi = h.roi_score
            lines.append(
                f"  {i}. [{h.vulnerability_type.value}] {h.endpoint.get('path', '(aggregate)')} "
                f"— priority={h.priority_score:.1f} ROI={roi:.1f} "
                f"L={h.likelihood:.2f} I={h.impact:.2f} E={h.exploitability:.2f} "
                f"${payout:.0f}"
            )
        return "\n".join(lines)
