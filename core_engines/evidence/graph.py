import threading
from typing import Any

from core_engines.validation.gate import Verdict
from core_engines.validation.replayer import ComparisonResult


class EvidenceGraph:
    def __init__(self):
        self._lock = threading.Lock()
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, str]] = []

    def add_comparison(
        self,
        hot_path_id: str,
        attempt: int,
        result: ComparisonResult,
        auth_label: str,
    ) -> str:
        node_id = f"comparison:{hot_path_id}:attempt_{attempt}"
        with self._lock:
            self._nodes[node_id] = {
                "type": "comparison",
                "hot_path_id": hot_path_id,
                "attempt": attempt,
                "status_match": result.status_match,
                "body_diff_ratio": result.body_diff_ratio,
                "sensitive_fields": result.sensitive_fields_detected,
                "consistent": result.consistent,
                "has_rate_limit": result.has_rate_limit,
                "has_timeout": result.has_timeout,
                "auth_label": auth_label,
                "baseline_hash": result.baseline.body_hash,
                "probe_hash": result.probe.body_hash,
                "baseline_status": result.baseline.status_code,
                "probe_status": result.probe.status_code,
                "timestamp": result.timestamp,
            }
        return node_id

    def add_verdict(self, verdict: Verdict) -> str:
        node_id = f"verdict:{verdict.hot_path_id}"
        with self._lock:
            self._nodes[node_id] = {
                "type": "verdict",
                "hot_path_id": verdict.hot_path_id,
                "status": verdict.status,
                "confidence": verdict.confidence,
                "reproducibility_score": verdict.reproducibility_score,
                "passed_rules": verdict.validation.passed_rules,
                "failed_rules": verdict.validation.failed_rules,
                "reason": verdict.reason,
                "retry_count": verdict.retry_count,
                "timestamp": verdict.timestamp,
            }
        return node_id

    def add_edge(self, from_id: str, to_id: str, relationship: str) -> None:
        with self._lock:
            self._edges.append({
                "from": from_id,
                "to": to_id,
                "relationship": relationship,
            })

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._nodes.get(node_id)

    def get_edges(self, node_id: str | None = None) -> list[dict[str, str]]:
        with self._lock:
            if node_id is None:
                return list(self._edges)
            return [
                e for e in self._edges
                if e["from"] == node_id or e["to"] == node_id
            ]

    def get_nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                n for n in self._nodes.values()
                if n.get("type") == node_type
            ]

    def get_verdicts(self) -> list[dict[str, Any]]:
        return self.get_nodes_by_type("verdict")

    def get_comparisons(self) -> list[dict[str, Any]]:
        return self.get_nodes_by_type("comparison")

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "nodes": dict(self._nodes),
                "edges": list(self._edges),
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceGraph":
        g = cls()
        g._nodes = dict(data.get("nodes", {}))
        g._edges = list(data.get("edges", []))
        return g
