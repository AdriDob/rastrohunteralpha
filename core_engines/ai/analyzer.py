from typing import Any

from core_engines.engine.unified_classifier import classify as unified_classify


class AIAnalyzer:
    """
    AI-powered endpoint analysis.

    Wraps the unified classifier with additional reasoning context.
    Intended to be expanded with LLM-based analysis in future iterations.
    """

    def analyze_endpoint(
        self,
        path: str,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        classification = unified_classify(path, method, params or {})
        return {
            "classification": classification,
            "technique": classification.get("technique", "unknown"),
            "vector": classification.get("vector_class", "unknown"),
            "confidence": classification.get("confidence", 0.0),
        }
