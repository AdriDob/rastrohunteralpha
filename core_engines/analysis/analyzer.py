from collections.abc import Iterable
from typing import Any

from core_engines.engine.unified_classifier import classify as unified_classify
from core_engines.engine.unified_classifier import synthesize_target_meta as unified_synthesize


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
        params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return unified_classify(path, method, params)

    def synthesize_target_meta(
        self,
        endpoints: Iterable[dict[str, Any]],
    ) -> dict[str, bool]:
        return unified_synthesize(endpoints)
