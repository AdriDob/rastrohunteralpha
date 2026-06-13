from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core_engines.execution.request_mutator import RequestMutator
from core_engines.validation.replayer import AuthContext, RequestSpec


@dataclass
class TestScenario:
    hot_path_id: str
    node_id: str
    attack_vector: str
    request_spec: RequestSpec
    mutations: Dict[str, str]
    auth_baseline: AuthContext
    auth_probe: AuthContext
    endpoint_signals: Dict[str, Any]
    template_name: str


class PoCGenerator:
    def __init__(self, mutator: Optional[RequestMutator] = None):
        self._mutator = mutator or RequestMutator()

    def build_test_plan(
        self,
        hot_paths: List[Dict[str, Any]],
        endpoint_details_map: Dict[str, Dict[str, Any]],
        endpoint_signals_map: Dict[str, Dict[str, Any]],
        baseline_token: Optional[str] = None,
        probe_token: Optional[str] = None,
    ) -> List[TestScenario]:
        scenarios: List[TestScenario] = []
        for hp in hot_paths:
            hp_id = hp.get("id") or hp.get("hot_path_id") or str(id(hp))
            template_name = hp.get("template", {}).get("name", "unknown") if isinstance(hp.get("template"), dict) else "unknown"
            for node_id in hp.get("nodes", []):
                details = endpoint_details_map.get(node_id, {})
                signals = endpoint_signals_map.get(node_id, {})
                attack_vector = self._detect_vector(node_id, signals)

                spec = RequestSpec(
                    url=details.get("url", ""),
                    method=details.get("method", "GET"),
                    headers=details.get("headers", {}),
                    params=details.get("params", {}),
                    body=details.get("body"),
                )

                mutations = self._mutator.build_mutations(
                    attack_vector,
                    details.get("path", ""),
                    spec.params,
                )

                auth_baseline, auth_probe = self._mutator.build_auth_contexts(
                    attack_vector,
                    baseline_token=baseline_token,
                    probe_token=probe_token,
                )

                scenarios.append(TestScenario(
                    hot_path_id=f"{hp_id}:{node_id}",
                    node_id=node_id,
                    attack_vector=attack_vector,
                    request_spec=spec,
                    mutations=mutations,
                    auth_baseline=auth_baseline,
                    auth_probe=auth_probe,
                    endpoint_signals=signals,
                    template_name=template_name,
                ))
        return scenarios

    def _detect_vector(self, node_id: str, signals: Dict[str, Any]) -> str:
        node_lower = node_id.lower()
        signals_list = signals.get("signals", []) if isinstance(signals, dict) else []
        attack_surface = signals.get("attack_surface", []) if isinstance(signals, dict) else []
        labels = signals.get("labels", []) if isinstance(signals, dict) else []

        if any(s in attack_surface for s in ("idor_candidate", "ownership_boundary")):
            return "IDOR"
        if any(s in signals_list for s in ("auth", "authentication")):
            return "Auth bypass"
        if any(s in attack_surface for s in ("data_exfiltration",)):
            return "Data exposure"
        if "graphql" in node_lower:
            return "GraphQL logic"
        if any(s in attack_surface for s in ("admin_surface",)):
            return "Privilege escalation"
        if any(s in signals_list for s in ("multi_tenant", "tenant_boundary")):
            return "Business logic"
        return "Business logic"
