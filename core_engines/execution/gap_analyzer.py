from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core_engines.execution.poc_generator import TestScenario
from core_engines.validation.gate import Verdict


@dataclass
class GapReport:
    coverage_score: float
    total_endpoints: int
    covered_endpoints: List[str]
    uncovered_endpoints: List[str]
    missing_hot_paths: List[Dict[str, Any]]
    under_tested_entities: List[str]
    blind_spots: List[Dict[str, str]]
    reinjection_plan: List[Dict[str, Any]]


class GapAnalyzer:
    def analyze(
        self,
        endpoints: List[Dict[str, Any]],
        test_scenarios: List[TestScenario],
        verdicts: Dict[str, Verdict],
        hot_paths: List[Dict[str, Any]],
        entity_endpoints: Optional[Dict[str, List[str]]] = None,
        auth_contexts: Optional[List[str]] = None,
    ) -> GapReport:
        entity_endpoints = entity_endpoints or {}
        auth_contexts = auth_contexts or ["authenticated", "anonymous"]

        all_endpoint_ids: Set[str] = set()
        for idx, ep in enumerate(endpoints):
            path = str(ep.get("path", "/"))
            method = str(ep.get("method", "GET")).upper()
            all_endpoint_ids.add(f"endpoint:{method}:{path}")

        covered_endpoints: Set[str] = set()
        used_hot_path_ids: Set[str] = set()

        for scenario in test_scenarios:
            covered_endpoints.add(scenario.node_id)
            used_hot_path_ids.add(scenario.hot_path_id)

        for hp in hot_paths:
            for node_id in hp.get("nodes", []):
                covered_endpoints.add(node_id)

        for v_id, verdict in verdicts.items():
            used_hot_path_ids.add(v_id)

        uncovered: List[str] = sorted(all_endpoint_ids - covered_endpoints)
        covered: List[str] = sorted(all_endpoint_ids & covered_endpoints)

        coverage_score = round(len(covered) / max(len(all_endpoint_ids), 1) * 100.0, 1)

        # Missing hot paths from uncovered endpoints
        missing_hot_paths = self._generate_missing_hot_paths(uncovered, endpoints)

        # Under-tested entities
        under_tested = self._find_under_tested_entities(entity_endpoints, covered)

        # Blind spots by auth context
        blind_spots = self._detect_blind_spots(uncovered, endpoints, auth_contexts)

        # Reinjection plan
        reinjection = self._build_reinjection_plan(missing_hot_paths, uncovered, endpoints)

        return GapReport(
            coverage_score=coverage_score,
            total_endpoints=len(all_endpoint_ids),
            covered_endpoints=covered,
            uncovered_endpoints=uncovered,
            missing_hot_paths=missing_hot_paths,
            under_tested_entities=under_tested,
            blind_spots=blind_spots,
            reinjection_plan=reinjection,
        )

    def _generate_missing_hot_paths(self, uncovered: List[str], endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ep_map = {}
        for ep in endpoints:
            method = str(ep.get("method", "GET")).upper()
            path = str(ep.get("path", "/"))
            eid = f"endpoint:{method}:{path}"
            ep_map[eid] = ep

        missing: List[Dict[str, Any]] = []
        for eid in uncovered:
            ep = ep_map.get(eid, {})
            missing.append({
                "node_id": eid,
                "method": ep.get("method", "GET"),
                "path": ep.get("path", "/"),
                "why_missing": "not_covered_by_any_test_scenario",
                "risk_score": float(ep.get("risk_score", 0)),
                "auth_context_needed": self._infer_auth_context(ep),
            })
        missing.sort(key=lambda x: x["risk_score"], reverse=True)
        return missing

    def _find_under_tested_entities(self, entity_endpoints: Dict[str, List[str]], covered: Set[str]) -> List[str]:
        under_tested: List[str] = []
        for entity, eids in entity_endpoints.items():
            covered_count = sum(1 for eid in eids if eid in covered)
            total = len(eids)
            if total > 0 and covered_count / total < 0.5:
                under_tested.append(entity)
        return under_tested

    def _detect_blind_spots(self, uncovered: List[str], endpoints: List[Dict[str, Any]], auth_contexts: List[str]) -> List[Dict[str, str]]:
        ep_map = {}
        for ep in endpoints:
            method = str(ep.get("method", "GET")).upper()
            path = str(ep.get("path", "/"))
            eid = f"endpoint:{method}:{path}"
            ep_map[eid] = ep

        spots: List[Dict[str, str]] = []
        for eid in uncovered:
            ep = ep_map.get(eid, {})
            spots.append({
                "endpoint_id": eid,
                "reason": "no_test_scenario",
                "auth_context": "anonymous" if not self._infer_auth_context(ep) else "authenticated",
            })
        return spots

    def _build_reinjection_plan(self, missing: List[Dict[str, Any]], uncovered: List[str], endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "node_id": m["node_id"],
                "action": "create_test_scenario",
                "priority": "high" if m["risk_score"] >= 50 else "medium" if m["risk_score"] >= 25 else "low",
                "risk_score": m["risk_score"],
            }
            for m in missing
        ]

    @staticmethod
    def _infer_auth_context(ep: Dict[str, Any]) -> bool:
        path = str(ep.get("path", "")).lower()
        labels = ep.get("labels", [])
        signals = ep.get("signals", [])
        if "auth" in labels or "auth" in signals:
            return True
        if any(kw in path for kw in ["login", "auth", "signin", "oauth", "token"]):
            return True
        return False
