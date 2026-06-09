import logging
from typing import Any, Dict, List, Optional

from core.execution.poc_generator import PoCGenerator, TestScenario
from core.validation.confidence import ConfidenceScorer
from core.validation.gate import Verdict
from core.validation.loop_engine import ValidationLoopEngine
from core.validation.replayer import RequestReplayer
from core.validation.rules import ValidationRuleSet

LOG = logging.getLogger("rastro.execution.differential")


class DifferentialEngine:
    def __init__(
        self,
        poc_generator: Optional[PoCGenerator] = None,
        vle: Optional[ValidationLoopEngine] = None,
    ):
        self._poc_generator = poc_generator or PoCGenerator()
        self._vle = vle or ValidationLoopEngine()

    def run(
        self,
        hot_paths: List[Dict[str, Any]],
        endpoint_details_map: Dict[str, Dict[str, Any]],
        endpoint_signals_map: Dict[str, Dict[str, Any]],
        baseline_token: Optional[str] = None,
        probe_token: Optional[str] = None,
        min_attempts: int = 3,
    ) -> Dict[str, Verdict]:
        scenarios = self._poc_generator.build_test_plan(
            hot_paths=hot_paths,
            endpoint_details_map=endpoint_details_map,
            endpoint_signals_map=endpoint_signals_map,
            baseline_token=baseline_token,
            probe_token=probe_token,
        )

        verdicts: Dict[str, Verdict] = {}
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
