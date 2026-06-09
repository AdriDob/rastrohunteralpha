from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


WEB3_RISK_WEIGHTS = {
    "rpc_method": 1.30,
    "contract_call": 1.20,
    "signature_auth": 1.25,
    "wallet_operation": 1.15,
    "onchain_query": 1.10,
}


@dataclass
class RebalancedScore:
    hot_path_id: str
    original_score: float
    adjusted_score: float
    drift: float
    reasons: List[str]


@dataclass
class RebalancerConfig:
    evidence_success_weight: float = 0.25
    historical_exploit_weight: float = 0.20
    cross_target_weight: float = 0.15
    web3_weight: float = 0.20
    time_decay_weight: float = 0.10
    coverage_penalty_weight: float = 0.10


class PriorityRebalancer:
    def __init__(self, config: Optional[RebalancerConfig] = None):
        self._config = config or RebalancerConfig()

    def rebalance(
        self,
        priorities: Dict[str, float],
        evidence_stats: Optional[Dict[str, Dict[str, Any]]] = None,
        historical_data: Optional[Dict[str, Any]] = None,
        cross_target_correlations: Optional[Dict[str, List[str]]] = None,
        web3_targets: Optional[Dict[str, str]] = None,
        coverage_report: Optional[Dict[str, Any]] = None,
        time_to_exploit: Optional[Dict[str, float]] = None,
    ) -> List[RebalancedScore]:
        evidence_stats = evidence_stats or {}
        historical_data = historical_data or {}
        cross_target_correlations = cross_target_correlations or {}
        web3_targets = web3_targets or {}
        coverage_report = coverage_report or {}
        time_to_exploit = time_to_exploit or {}

        rebalanced: List[RebalancedScore] = []

        for hot_path_id, score in priorities.items():
            adjustments: List[str] = []
            adjusted = score

            ev_factor = self._evidence_success_factor(hot_path_id, evidence_stats)
            adjusted += ev_factor * self._config.evidence_success_weight
            if ev_factor != 0:
                adjustments.append(f"evidence_success: {ev_factor:+.2f}")

            hist_factor = self._historical_exploit_factor(hot_path_id, historical_data)
            adjusted += hist_factor * self._config.historical_exploit_weight
            if hist_factor != 0:
                adjustments.append(f"historical_exploit: {hist_factor:+.2f}")

            cross_factor = self._cross_target_factor(hot_path_id, cross_target_correlations)
            adjusted += cross_factor * self._config.cross_target_weight
            if cross_factor != 0:
                adjustments.append(f"cross_target: {cross_factor:+.2f}")

            web3_factor = self._web3_risk_factor(hot_path_id, web3_targets)
            adjusted += web3_factor * self._config.web3_weight
            if web3_factor != 0:
                adjustments.append(f"web3_weight: {web3_factor:+.2f}")

            time_factor = self._time_decay_factor(hot_path_id, time_to_exploit)
            adjusted += time_factor * self._config.time_decay_weight
            if time_factor != 0:
                adjustments.append(f"time_drift: {time_factor:+.2f}")

            coverage_factor = self._coverage_penalty(hot_path_id, coverage_report)
            adjusted += coverage_factor * self._config.coverage_penalty_weight
            if coverage_factor != 0:
                adjustments.append(f"coverage: {coverage_factor:+.2f}")

            adjusted = max(0.0, min(100.0, adjusted))
            drift = adjusted - score

            rebalanced.append(RebalancedScore(
                hot_path_id=hot_path_id,
                original_score=score,
                adjusted_score=round(adjusted, 1),
                drift=round(drift, 1),
                reasons=adjustments,
            ))

        rebalanced.sort(key=lambda r: r.adjusted_score, reverse=True)
        return rebalanced

    def reorder_hot_paths(self, hot_paths: List[Any], rebalanced: List[RebalancedScore]) -> List[Any]:
        score_map: Dict[str, float] = {r.hot_path_id: r.adjusted_score for r in rebalanced}
        def _key(hp: Any) -> float:
            if hasattr(hp, 'nodes') and hp.nodes:
                return score_map.get(hp.nodes[0], 0.0)
            if isinstance(hp, dict):
                nodes = hp.get("nodes", [""])
                return score_map.get(nodes[0] if nodes else "", 0.0)
            return 0.0
        sorted_hot_paths = sorted(hot_paths, key=_key, reverse=True)
        return sorted_hot_paths

    def _evidence_success_factor(self, hot_path_id: str, evidence_stats: Dict[str, Dict[str, Any]]) -> float:
        stats = evidence_stats.get(hot_path_id)
        if not stats:
            return 0.0
        confirmed = stats.get("confirmed", 0)
        total = stats.get("total", 1)
        rate = confirmed / max(total, 1)
        if rate >= 0.8:
            return 10.0
        if rate >= 0.5:
            return 5.0
        return -5.0

    def _historical_exploit_factor(self, hot_path_id: str, historical_data: Dict[str, Any]) -> float:
        records = historical_data.get(hot_path_id, [])
        if not isinstance(records, list) or not records:
            return 0.0
        exploited_count = sum(1 for r in records if isinstance(r, dict) and r.get("exploitable", False))
        rate = exploited_count / len(records)
        if rate >= 0.7:
            return 15.0
        if rate >= 0.3:
            return 8.0
        return -3.0

    def _cross_target_factor(self, hot_path_id: str, correlations: Dict[str, List[str]]) -> float:
        related = correlations.get(hot_path_id, [])
        if len(related) >= 5:
            return 12.0
        if len(related) >= 3:
            return 8.0
        if len(related) >= 1:
            return 4.0
        return 0.0

    def _web3_risk_factor(self, hot_path_id: str, web3_targets: Dict[str, str]) -> float:
        target_type = web3_targets.get(hot_path_id)
        if not target_type:
            return 0.0
        weight = WEB3_RISK_WEIGHTS.get(target_type, 1.0)
        return (weight - 1.0) * 50.0

    def _time_decay_factor(self, hot_path_id: str, time_to_exploit: Dict[str, float]) -> float:
        tte = time_to_exploit.get(hot_path_id)
        if tte is None:
            return 0.0
        if tte > 30:
            return -5.0
        if tte > 14:
            return -2.0
        if tte < 3:
            return 5.0
        return 2.0

    def _coverage_penalty(self, hot_path_id: str, coverage_report: Dict[str, Any]) -> float:
        uncovered = coverage_report.get("uncovered_endpoints", [])
        if not uncovered:
            return 0.0
        if hot_path_id in uncovered:
            return -10.0
        return 0.0
