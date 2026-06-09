import json
import logging
from typing import Any, Dict, List, Optional

from core.ai.assistant import ScanAssistant
from core.analysis.investigation_graph import InvestigationGraphBuilder
from core.engine.unified_scoring import score as unified_score
from core.analysis.noise_reduction import NoiseReductionEngine
from core.attack.engine import AttackDecisionEngine
from core.evidence.graph import EvidenceGraph
from core.evidence.store import EvidenceStore
from core.execution.differential_engine import DifferentialEngine
from core.execution.gap_analyzer import GapAnalyzer
from core.execution.poc_generator import PoCGenerator
from core.memory.identity_graph import IdentityGraph
from core.reporting.report_engine import ProgramData, ReportEngine
from core.engine.priority_rebalancer import PriorityRebalancer
from core.validation.gate import Verdict

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

    def run(
        self,
        endpoints: List[Dict[str, Any]],
        baseline_token: Optional[str] = None,
        probe_token: Optional[str] = None,
        program_data: Optional[ProgramData] = None,
    ) -> Dict[str, Any]:
        if not endpoints:
            return {"status": "no_endpoints", "verdicts": {}, "reports": []}

        LOG.info("Pipeline: scoring %d endpoints", len(endpoints))
        scored = self._score_endpoints(endpoints)

        LOG.info("Pipeline: noise reduction (%d input)", len(scored))
        noise_result = self.noise_filter.analyze(scored)
        clean = noise_result.clean_endpoints
        LOG.info("Pipeline: %d clean, %d noise", len(clean), len(noise_result.noise_endpoints))

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
            }

        endpoint_details_map: Dict[str, Dict[str, Any]] = {}
        endpoint_signals_map: Dict[str, Dict[str, Any]] = {}
        entity_endpoints_map: Dict[str, List[str]] = {}
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
        priority_map: Dict[str, float] = {}
        for hp in hot_paths:
            if hp.nodes:
                priority_map[hp.nodes[0]] = float(
                    endpoint_signals_map.get(hp.nodes[0], {}).get("risk_score", 0)
                )
        web3_targets: Dict[str, str] = {}
        for node_id, signals in endpoint_signals_map.items():
            if "web3" in signals.get("signals", []):
                web3_targets[node_id] = "rpc_method"
        rebalanced = self.priority_rebalancer.rebalance(
            priorities=priority_map,
            web3_targets=web3_targets,
        )
        if rebalanced:
            hot_paths = self.priority_rebalancer.reorder_hot_paths(hot_paths, rebalanced)

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
        confirmed: List[Verdict] = []
        verdict_db_ids: Dict[str, int] = {}
        for hp_idx, hp in enumerate(hot_paths):
            for node_id in hp.nodes:
                hp_key = f"{hp_idx}:{node_id}"
                verdict = verdicts.get(hp_key)
                if verdict is None:
                    continue
                self.evidence_graph.add_verdict(verdict)
                endpoint_id = self._resolve_endpoint_id(node_id)
                db_id = self.evidence_store.save_verdict(verdict, endpoint_id=endpoint_id)
                verdict_db_ids[verdict.hot_path_id] = db_id
                if verdict.status == "confirmed":
                    confirmed.append(verdict)

        LOG.info("Pipeline: %d confirmed findings, building reports", len(confirmed))
        reports = []
        for verdict in confirmed:
            node_id = verdict.hot_path_id.split(":", 1)[1] if ":" in verdict.hot_path_id else ""
            ep_data = endpoint_details_map.get(node_id, {})
            verdict_db_id = verdict_db_ids.get(verdict.hot_path_id, 0)
            evidence = self.evidence_store.get_evidence_for_verdict(verdict_db_id) if verdict_db_id else []
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

        return {
            "status": "completed",
            "total_endpoints": len(endpoints),
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
        }

    def _score_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    def _node_to_url(node_id: str, meta: Dict[str, Any]) -> str:
        path = meta.get("path", "")
        return f"https://target.example.com{path}"

    @staticmethod
    def _resolve_endpoint_id(node_id: str) -> Optional[int]:
        import re
        match = re.search(r"endpoint:(\w+):(.+)", node_id)
        if match:
            from database import models
            from database.db import SessionLocal
            session = SessionLocal()
            try:
                method = match.group(1)
                path = match.group(2)
                ep = session.query(models.Endpoint).filter(
                    models.Endpoint.method == method,
                    models.Endpoint.path == path,
                ).first()
                return ep.id if ep else None
            finally:
                session.close()
        return None
