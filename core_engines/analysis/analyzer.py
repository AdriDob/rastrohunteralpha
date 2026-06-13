from typing import Dict, Iterable, Any

from core_engines.engine.unified_scoring import score as unified_score
from core_engines.engine.unified_classifier import classify as unified_classify, synthesize_target_meta as unified_synthesize


class EndpointAnalyzer:
    """
    Legacy compatibility wrapper.
    Delegates to core.engine.unified_classifier.
    Will be removed once all consumers migrate to unified functions.
    """

    def classify_endpoint(
        self,
        path: str,
        method: str,
        params: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        return unified_classify(path, method, params)

    def synthesize_target_meta(
        self,
        endpoints: Iterable[Dict[str, Any]],
    ) -> Dict[str, bool]:
        return unified_synthesize(endpoints)