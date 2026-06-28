import json
import logging
from typing import Any

from core_engines.ai.assistant import ScanAssistant
from core_engines.analysis.investigation_graph import InvestigationGraphBuilder
from core_engines.analysis.noise_reduction import NoiseReductionEngine
from core_engines.attack.engine import AttackDecisionEngine
from core_engines.engine.hypothesis.engine import HypothesisEngine
from core_engines.engine.priority_rebalancer import PriorityRebalancer
from core_engines.engine.risk_model import AttackSurfaceMapper, ROIEstimator
from core_engines.engine.snapshot import from_pipeline_output
from core_engines.engine.unified_scoring import score as unified_score
from core_engines.evidence.graph import EvidenceGraph
from core_engines.evidence.store import EvidenceStore
from core_engines.execution.differential_engine import DifferentialEngine
from core_engines.execution.gap_analyzer import GapAnalyzer
from core_engines.execution.poc_generator import PoCGenerator
from core_engines.memory.identity_graph import IdentityGraph
from core_engines.observability import timer
from core_engines.reporting.report_engine import ProgramData, ReportEngine
from core_engines.targets.technology import fingerprint_program
from core_engines.validation.gate import Verdict

LOG = logging.getLogger("rastro.pipeline")


class Pipeline:
    def __init__(self):
        self.noise_filter = NoiseReductionEngine()
        self.graph_builder = InvestigationGraphBuilder()
        self.attack_engine = AttackDecisionEngine()
        self.poc_gen = PoCGenerator()
        self.diff_engine = DifferentialEngine()
        self.evidence_graph = EvidenceGraph()
        self.evidence_store = EvidenceStore()
        self.report_engine = ReportEngine(evidence_store=self.evidence_store)
        self.gap_analyzer = GapAnalyzer()
        self.priority_rebalancer = PriorityRebalancer()
        self.identity_graph = IdentityGraph()
        self.assistant = ScanAssistant(
            evidence_graph=self.evidence_graph,
            report_engine=self.report_engine,
            scorer=None,
        )
        self.surface_mapper = AttackSurfaceMapper()
        self.roi_estimator = ROIEstimator()
        self.hypothesis_engine = HypothesisEngine(enable_llm=False)

    def run(
        self,
        endpoints: list[dict[str, Any]],
        baseline_token: str | None = None,
        probe_token: str | None = None,
        program_data: ProgramData | None = None,
        target_id: int = 0,
        target_name: str = "",
    ) -> dict[str, Any]:
        if not endpoints:
            return {"status": "no_endpoints", "verdicts": {}, "reports": []}

        with timer("pipeline.score"):
            LOG.info("Pipeline: scoring %d endpoints", len(endpoints))
            scored = self._score_endpoints(endpoints)

        with timer("pipeline.noise_reduction"):
            LOG.info("Pipeline: noise reduction (%d input)", len(scored))
            noise_result = self.noise_filter.analyze(scored)
            clean = noise_result.clean_endpoints
            LOG.info("Pipeline: %d clean, %d noise", len(clean), len(noise_result.noise_endpoints))

        # Attack surface mapping + ROI estimation for clean endpoints
        with timer("pipeline.surface_mapping"):
            LOG.info("Pipeline: mapping attack surface (%d clean)", len(clean))

            # Detect technologies from target metadata
            technologies = self._detect_technologies(target_id, target_name)
            if technologies:
                LOG.info("Pipeline: detected %d technologies for target", len(technologies))

            # Extract suspicious discovered paths from clean endpoints
            discovered_paths = self._extract_discovered_paths(clean)
            if discovered_paths:
                LOG.info("Pipeline: %d suspicious discovered paths found", len(discovered_paths))

            surface_map = self.surface_mapper.map(clean, technologies=technologies, discovered_paths=discovered_paths)
            for ep in clean:
                ep["roi"] = vars(self.roi_estimator.estimate(ep))
            LOG.info(
                "Pipeline: surface: %d IDOR clusters, %d auth boundaries, %d multi-tenant, %d GraphQL",
                len(surface_map.idor_clusters),
                len(surface_map.auth_boundaries),
                len(surface_map.multi_tenant_zones),
                len(surface_map.graphql_surfaces),
            )

        with timer("pipeline.investigation_graph"):
            LOG.info("Pipeline: building investigation graph")
            inv_report = self.graph_builder.build(clean)
            hot_paths = inv_report.hot_paths
            LOG.info("Pipeline: %d hot paths detected", len(hot_paths))

        if not hot_paths:
            return {
                "status": "no_hot_paths",
                "verdicts": {},
                "reports": [],
                "noise_ratio": noise_result.noise_ratio,
                "surface_map": vars(surface_map),
            }

        endpoint_details_map: dict[str, dict[str, Any]] = {}
        endpoint_signals_map: dict[str, dict[str, Any]] = {}
        entity_endpoints_map: dict[str, list[str]] = {}
        for node in inv_report.graph.get("nodes", []):
            node_id = node.get("node_id", "")
            ntype = node.get("type", "")
            meta = node.get("metadata", {})
            url = self._node_to_url(node_id, meta)
            method = meta.get("method", "GET")
            params = {p: "test" for p in meta.get("params", [])}
            endpoint_details_map[node_id] = {
                "url": url,
                "method": method,
                "path": meta.get("path", ""),
                "params": params,
                "headers": {},
            }
            endpoint_signals_map[node_id] = {
                "risk_score": meta.get("risk_score", 0),
                "labels": meta.get("labels", []),
                "signals": meta.get("signals", []),
                "attack_surface": meta.get("attack_surface", []),
            }
            if ntype in ("entity", "web3_entity"):
                entity_endpoints_map.setdefault(meta.get("value", "unknown"), []).append(node_id)

        # Identity graph: scan endpoints for identity tokens and propagate
        LOG.info("Pipeline: building identity graph across endpoints")
        for node_id, details in endpoint_details_map.items():
            path = details.get("path", "")
            identities = self.identity_graph.scan_for_identities(path)
            for raw_id, entity_type in identities.items():
                self.identity_graph.tokenize(raw_id, entity_type=entity_type, source_endpoint=node_id)
        self.identity_graph.link_endpoints_by_identity(endpoint_details_map)
        identity_chains = self.identity_graph.detect_reuse(list(endpoint_details_map.keys()))
        if identity_chains:
            LOG.info("Pipeline: %d identity reuse chains detected", len(identity_chains))

        # Priority rebalancing before validation
        LOG.info("Pipeline: rebalancing priorities across %d hot paths", len(hot_paths))
        priority_map: dict[str, float] = {}
        for hp in hot_paths:
            if hp.nodes:
                priority_map[hp.nodes[0]] = float(
                    endpoint_signals_map.get(hp.nodes[0], {}).get("risk_score", 0)
                )
        web3_targets: dict[str, str] = {}
        for node_id, signals in endpoint_signals_map.items():
            if "web3" in signals.get("signals", []):
                web3_targets[node_id] = "rpc_method"
        rebalanced = self.priority_rebalancer.rebalance(
            priorities=priority_map,
            web3_targets=web3_targets,
        )
        if rebalanced:
            hot_paths = self.priority_rebalancer.reorder_hot_paths(hot_paths, rebalanced)

        # Hypothesis generation — turns hot paths into actionable attack hypotheses
        if target_id and target_name:
            LOG.info("Pipeline: generating hypotheses for target %s", target_name)
            try:
                hp_dicts = [
                    {
                        "nodes": hp.nodes,
                        "template": getattr(hp, "why_it_matters", ""),
                        "bridge_entity": "",
                        "reward": getattr(hp, "estimated_reward", "medium"),
                    }
                    for hp in hot_paths
                ]
                hypothesis_output = self.hypothesis_engine.run(
                    target_id=target_id,
                    target_name=target_name,
                    endpoints=clean,
                    attack_surface_map=vars(surface_map),
                    hot_paths=hp_dicts,
                )
                LOG.info("Pipeline: %d hypotheses generated", hypothesis_output.total_hypotheses)
            except Exception as exc:
                LOG.warning("Pipeline: hypothesis generation failed: %s", exc)
                hypothesis_output = None
        else:
            hypothesis_output = None

        with timer("pipeline.differential_validation"):
            LOG.info("Pipeline: running differential validation on %d hot paths", len(hot_paths))
            verdicts = self.diff_engine.run(
                hot_paths=[{"id": str(i), "nodes": hp.nodes} for i, hp in enumerate(hot_paths)],
                endpoint_details_map=endpoint_details_map,
                endpoint_signals_map=endpoint_signals_map,
                baseline_token=baseline_token,
                probe_token=probe_token,
                min_attempts=3,
            )

        LOG.info("Pipeline: persisting verdicts and evidence")
        confirmed: list[Verdict] = []
        verdict_db_ids: dict[str, int] = {}

        # Batch-resolve endpoint IDs for all node_ids across all hot_paths
        all_node_ids = list({nid for hp in hot_paths for nid in hp.nodes})
        endpoint_id_cache = self._batch_resolve_endpoint_ids(all_node_ids)

        for hp_idx, hp in enumerate(hot_paths):
            for node_id in hp.nodes:
                hp_key = f"{hp_idx}:{node_id}"
                verdict = verdicts.get(hp_key)
                if verdict is None:
                    continue
                self.evidence_graph.add_verdict(verdict)
                endpoint_id = endpoint_id_cache.get(node_id)
                db_id = self.evidence_store.save_verdict(verdict, endpoint_id=endpoint_id)
                verdict_db_ids[verdict.hot_path_id] = db_id
                if verdict.status == "confirmed":
                    confirmed.append(verdict)

        LOG.info("Pipeline: %d confirmed findings, building reports", len(confirmed))
        reports = []
        if confirmed:
            # Batch-load evidence for all confirmed verdicts at once
            all_verdict_db_ids = [
                verdict_db_ids.get(v.hot_path_id, 0) for v in confirmed
            ]
            batch_evidence = self.evidence_store.batch_get_evidence_for_verdicts(all_verdict_db_ids)
            for verdict in confirmed:
                node_id = verdict.hot_path_id.split(":", 1)[1] if ":" in verdict.hot_path_id else ""
                ep_data = endpoint_details_map.get(node_id, {})
                verdict_db_id = verdict_db_ids.get(verdict.hot_path_id, 0)
                evidence = batch_evidence.get(verdict_db_id, [])
                report = self.report_engine.build(
                    verdict, program_data=program_data, endpoint_data=ep_data, evidence_list=evidence,
                )
                if report:
                    reports.append(report)

        # Gap analysis: compute coverage and detect blind spots
        LOG.info("Pipeline: running gap analysis")
        scored_test_scenarios = []
        for hp_idx, hp in enumerate(hot_paths):
            for node_id in hp.nodes:
                hp_key = f"{hp_idx}:{node_id}"
                if hp_key in verdicts:
                    scored_test_scenarios.append(self.poc_gen.build_test_plan(
                        hot_paths=[{"id": str(hp_idx), "nodes": hp.nodes}],
                        endpoint_details_map={node_id: endpoint_details_map.get(node_id, {})},
                        endpoint_signals_map={node_id: endpoint_signals_map.get(node_id, {})},
                    )[0] if endpoint_details_map.get(node_id) else None)

        scored_test_scenarios = [s for s in scored_test_scenarios if s is not None]
        gap_report = self.gap_analyzer.analyze(
            endpoints=clean,
            test_scenarios=scored_test_scenarios,
            verdicts=verdicts,
            hot_paths=[{"nodes": hp.nodes} for hp in hot_paths],
            entity_endpoints=entity_endpoints_map,
        )

        # Generate assistant narrative
        verdict_dicts = [
            {"hot_path_id": v.hot_path_id, "status": v.status, "confidence": v.confidence, "reason": v.reason, "passed_rules": v.validation.passed_rules, "failed_rules": v.validation.failed_rules}
            for v in verdicts.values()
        ]
        assistant_summary = self.assistant.summarize_scan(
            scan_id="pipeline_run",
            endpoint_count=len(endpoints),
            verdicts=verdict_dicts,
            reports=reports,
        )

        result: dict[str, Any] = {
            "status": "completed",
            "total_endpoints": len(endpoints),
            "endpoints": clean,
            "clean_endpoints": len(clean),
            "noise_ratio": noise_result.noise_ratio,
            "hot_paths_found": len(hot_paths),
            "verdicts": {
                k: {"status": v.status, "confidence": v.confidence, "reason": v.reason}
                for k, v in verdicts.items()
            },
            "confirmed_count": len(confirmed),
            "reports": [
                {"title": r.title, "severity": r.severity, "endpoint": r.affected_endpoint}
                for r in reports
            ],
            "coverage_score": gap_report.coverage_score,
            "uncovered_endpoints": gap_report.uncovered_endpoints[:10],
            "missing_hot_paths": [m["node_id"] for m in gap_report.missing_hot_paths[:5]],
            "identity_chains": len(identity_chains),
            "assistant_summary": assistant_summary,
            "surface_map": {
                "idor_clusters": [
                    {"path": e.get("path"), "method": e.get("method"), "risk_score": e.get("risk_score")}
                    for e in surface_map.idor_clusters
                ],
                "auth_boundaries": [
                    {"path": e.get("path"), "method": e.get("method"), "risk_score": e.get("risk_score")}
                    for e in surface_map.auth_boundaries
                ],
                "multi_tenant_zones": [
                    {"path": e.get("path"), "method": e.get("method"), "risk_score": e.get("risk_score")}
                    for e in surface_map.multi_tenant_zones
                ],
                "graphql_surfaces": [
                    {"path": e.get("path"), "method": e.get("method"), "risk_score": e.get("risk_score")}
                    for e in surface_map.graphql_surfaces
                ],
            },
        }

        if hypothesis_output:
            result["hypotheses"] = {
                "total": hypothesis_output.total_hypotheses,
                "by_source": hypothesis_output.by_source,
                "by_type": hypothesis_output.by_type,
                "avg_roi": hypothesis_output.avg_roi,
                "max_roi": hypothesis_output.max_roi,
                "profitable_count": hypothesis_output.profitable_count,
                "summary": hypothesis_output.summary,
                "queue": [
                    {
                        "id": h.id,
                        "vulnerability_type": h.vulnerability_type.value,
                        "priority_score": h.priority_score,
                        "roi_score": h.roi_score,
                        "likelihood": h.likelihood,
                        "impact": h.impact,
                        "exploitability": h.exploitability,
                        "reasoning": h.reasoning[:200],
                        "vector": h.vector,
                        "source": h.source.value,
                    }
                    for h in hypothesis_output.attack_queue.prioritized()[:20]
                ],
            }

        # Build canonical snapshot
        try:
            target_info = {"id": target_id, "name": target_name} if target_id else None
            result["snapshot"] = from_pipeline_output(result, target_info)
        except Exception as exc:
            LOG.warning("Pipeline: snapshot build failed: %s", exc)

        return result

    def _score_endpoints(self, endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored = []
        for ep in endpoints:
            path = str(ep.get("path", "/"))
            method = str(ep.get("method", "GET")).upper()
            params = ep.get("params", {})
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except (json.JSONDecodeError, ValueError):
                    params = {}
            result = unified_score(path, method, params)
            result["path"] = path
            result["method"] = method
            result["params"] = params
            scored.append(result)
        return scored

    @staticmethod
    def _detect_technologies(target_id: int, target_name: str) -> list[dict[str, Any]]:
        """Detect technologies for a target from metadata and stored program intel."""
        technologies: list[dict[str, Any]] = []
        if not target_id and not target_name:
            return technologies

        try:
            from database.db import SessionLocal
            from database.models import TargetIntel

            session = SessionLocal()
            try:
                records = session.query(TargetIntel).filter(
                    TargetIntel.name.ilike(f"%{target_name}%")
                ).all()
                for rec in records:
                    if rec.technology_tags:
                        for tag in rec.technology_tags.split(","):
                            tag = tag.strip()
                            if tag and not any(t.get("name") == tag for t in technologies):
                                technologies.append({"name": tag, "version": "", "source": rec.source or "intel"})
            finally:
                session.close()
        except Exception as exc:
            LOG.debug("Pipeline: technology detection failed: %s", exc)

        if not technologies and target_name:
            try:
                tags = fingerprint_program({"name": target_name})
                for tag in tags:
                    if not any(t.get("name") == tag for t in technologies):
                        technologies.append({"name": tag, "version": "", "source": "fingerprint"})
            except Exception as exc:
                LOG.debug("Pipeline: fingerprint_program failed: %s", exc)

        return technologies

    @staticmethod
    def _extract_discovered_paths(endpoints: list[dict[str, Any]]) -> list[str]:
        """Extract suspicious paths from clean endpoints for hypothesis generation."""
        suspicious_suffixes = {
            ".git/config", ".env", "wp-config.php.bak", "backup.sql",
            "sitemap.xml", "robots.txt", "crossdomain.xml",
            "client-access-policy.xml", "actuator/health", "actuator/env",
            "swagger/v1/swagger.json", "api-docs", "graphql",
            "console", "actuator/gateway/routes",
        }
        paths: list[str] = []
        seen: set = set()
        for ep in endpoints:
            path = str(ep.get("path", ""))
            lower = path.lower().strip("/").rstrip("/")
            for suffix in suspicious_suffixes:
                if lower.endswith(suffix) and path not in seen:
                    seen.add(path)
                    paths.append(path)
                    break
        return paths

    @staticmethod
    def _node_to_url(node_id: str, meta: dict[str, Any]) -> str:
        path = meta.get("path", "")
        return f"https://target.example.com{path}"

    @staticmethod
    def _batch_resolve_endpoint_ids(node_ids: list[str]) -> dict[str, int | None]:
        import re

        from database import models
        from database.db import SessionLocal

        cache: dict[str, int | None] = {}
        method_path_pairs: list[tuple] = []
        id_to_pair: dict[str, tuple] = {}

        for nid in node_ids:
            match = re.search(r"endpoint:(\w+):(.+)", nid)
            if match:
                m, p = match.group(1), match.group(2)
                method_path_pairs.append((m, p))
                id_to_pair[nid] = (m, p)
                cache[nid] = None

        if not method_path_pairs:
            return cache

        session = SessionLocal()
        try:
            from sqlalchemy import or_
            clauses = [
                (models.Endpoint.method == m) & (models.Endpoint.path == p)
                for m, p in method_path_pairs
            ]
            if clauses:
                rows = session.query(models.Endpoint).filter(or_(*clauses)).all()
                lookup = {(r.method, r.path): r.id for r in rows}
                for nid, (m, p) in id_to_pair.items():
                    cache[nid] = lookup.get((m, p))
        finally:
            session.close()
        return cache
