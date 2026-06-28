import logging
from typing import Any

from core_engines.execution.poc_generator import PoCGenerator
from core_engines.validation.gate import Verdict
from core_engines.validation.loop_engine import ValidationLoopEngine

LOG = logging.getLogger("rastro.execution.differential")


class DifferentialEngine:
    def __init__(
        self,
        poc_generator: PoCGenerator | None = None,
        vle: ValidationLoopEngine | None = None,
    ):
        self._poc_generator = poc_generator or PoCGenerator()
        self._vle = vle or ValidationLoopEngine()

    def run(
        self,
        hot_paths: list[dict[str, Any]],
        endpoint_details_map: dict[str, dict[str, Any]],
        endpoint_signals_map: dict[str, dict[str, Any]],
        baseline_token: str | None = None,
        probe_token: str | None = None,
        min_attempts: int = 3,
    ) -> dict[str, Verdict]:
        scenarios = self._poc_generator.build_test_plan(
            hot_paths=hot_paths,
            endpoint_details_map=endpoint_details_map,
            endpoint_signals_map=endpoint_signals_map,
            baseline_token=baseline_token,
            probe_token=probe_token,
        )

        verdicts: dict[str, Verdict] = {}
        for scenario in scenarios:
            verdict = self._vle.evaluate(
                hot_path_id=scenario.hot_path_id,
                endpoint_details={
                    "url": scenario.request_spec.url,
                    "method": scenario.request_spec.method,
                    "headers": scenario.request_spec.headers,
                    "params": scenario.request_spec.params,
                    "body": scenario.request_spec.body,
                },
                endpoint_signals=scenario.endpoint_signals,
                auth_baseline=scenario.auth_baseline,
                auth_probe=scenario.auth_probe,
                mutations=scenario.mutations,
                min_attempts=min_attempts,
            )
            verdicts[scenario.hot_path_id] = verdict
            LOG.info(
                "Verdict %s: %s (confidence=%.2f, rules=%s)",
                scenario.hot_path_id, verdict.status,
                verdict.confidence, verdict.validation.passed_rules,
            )
        return verdicts
