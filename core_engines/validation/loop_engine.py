from datetime import datetime, timezone
from typing import Any

from core_engines.validation.confidence import ConfidenceScorer
from core_engines.validation.gate import ReportGate, Verdict
from core_engines.validation.replayer import AuthContext, RequestReplayer, RequestSpec
from core_engines.validation.rules import ValidationRuleSet

DEFAULT_CONCURRENCY = 5


class ValidationLoopEngine:
    def __init__(
        self,
        replayer: RequestReplayer | None = None,
        rules: ValidationRuleSet | None = None,
        scorer: ConfidenceScorer | None = None,
        gate: ReportGate | None = None,
    ):
        self._replayer = replayer or RequestReplayer()
        self._rules = rules or ValidationRuleSet()
        self._scorer = scorer or ConfidenceScorer()
        self._gate = gate or ReportGate()

    def evaluate(
        self,
        hot_path_id: str,
        endpoint_details: dict[str, Any],
        endpoint_signals: dict[str, Any],
        auth_baseline: AuthContext,
        auth_probe: AuthContext,
        mutations: dict[str, str] | None = None,
        min_attempts: int = 3,
    ) -> Verdict:
        request_spec = RequestSpec(
            url=endpoint_details.get("url", ""),
            method=endpoint_details.get("method", "GET"),
            headers=endpoint_details.get("headers", {}),
            params=endpoint_details.get("params", {}),
            body=endpoint_details.get("body"),
        )

        comparison_results = self._replayer.revalidate(
            request_spec=request_spec,
            auth_baseline=auth_baseline,
            auth_probe=auth_probe,
            mutations=mutations or {},
            min_attempts=min_attempts,
        )

        validation_report = self._rules.evaluate(comparison_results)

        confidence = self._scorer.calculate(
            results=comparison_results,
            validation=validation_report,
            endpoint_signals=endpoint_signals,
        )

        consistent_count = sum(1 for r in comparison_results if r.consistent)
        reproducibility_score = consistent_count / max(len(comparison_results), 1)

        if self._gate.admit(Verdict(
            hot_path_id=hot_path_id,
            status="confirmed",
            confidence=confidence.score,
            reproducibility_score=reproducibility_score,
            validation=validation_report,
            confidence_details=confidence,
            evidence_links=[],
            reason="",
            retry_count=len(comparison_results),
            timestamp="",
        )):
            passed = validation_report.passed_rules
            status = "confirmed"
            reason = (
                f"Confirmed: {len(passed)} rule(s) passed ({', '.join(passed)}), "
                f"confidence={confidence.score:.2f} ({confidence.level}), "
                f"reproducibility={reproducibility_score:.2f}"
            )
        elif confidence.score >= 0.3:
            status = "inconclusive"
            reason = (
                f"Inconclusive: confidence={confidence.score:.2f} below 0.6 threshold, "
                f"reproducibility={reproducibility_score:.2f}, "
                f"rules passed={validation_report.passed_rules}"
            )
        else:
            status = "rejected"
            reason = (
                f"Rejected: confidence={confidence.score:.2f}, "
                f"reproducibility={reproducibility_score:.2f}, "
                f"rules passed={validation_report.passed_rules}"
            )

        evidence_links = [
            f"attempt_{r.attempt}" for r in comparison_results if r.consistent
        ]

        return Verdict(
            hot_path_id=hot_path_id,
            status=status,
            confidence=confidence.score,
            reproducibility_score=reproducibility_score,
            validation=validation_report,
            confidence_details=confidence,
            evidence_links=evidence_links,
            reason=reason,
            retry_count=len(comparison_results),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def evaluate_all(
        self,
        hot_paths: list[dict[str, Any]],
        endpoint_details_map: dict[str, dict[str, Any]],
        endpoint_signals_map: dict[str, dict[str, Any]],
        auth_baseline: AuthContext,
        auth_probe: AuthContext,
        mutations_map: dict[str, dict[str, str]] | None = None,
        min_attempts: int = 3,
    ) -> dict[str, Verdict]:
        verdicts: dict[str, Verdict] = {}
        for hp in hot_paths:
            hp_id = hp.get("id") or hp.get("hot_path_id") or str(id(hp))
            for node_id in hp.get("nodes", []):
                details = endpoint_details_map.get(node_id, {})
                signals = endpoint_signals_map.get(node_id, {})
                mutations = (mutations_map or {}).get(node_id, {})
                verdict = self.evaluate(
                    hot_path_id=f"{hp_id}:{node_id}",
                    endpoint_details=details,
                    endpoint_signals=signals,
                    auth_baseline=auth_baseline,
                    auth_probe=auth_probe,
                    mutations=mutations,
                    min_attempts=min_attempts,
                )
                verdicts[verdict.hot_path_id] = verdict
        return verdicts
