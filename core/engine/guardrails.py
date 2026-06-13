"""
guardrails — Architectural enforcement for Rastro's single-source-of-truth.

ONLY_PIPELINE_CAN_SCORE = True

This module provides runtime enforcement hooks and documentation
to ensure no component computes its own risk_score outside of
core/engine/unified_scoring.py.
"""

ONLY_PIPELINE_CAN_SCORE = True

SOURCE_OF_TRUTH = "core.engine.unified_scoring.score"

AUTHORIZED_SCORING_CONSUMERS = {
    "core.engine.unified_scoring",
    "core.engine.unified_classifier",
    "core.engine.priority_rebalancer",
    "core.engine.risk_model",
}

FORBIDDEN_IMPORTS: set[str] = {
    "core.targets.scorer",
}


class ScoringViolationError(RuntimeError):
    """
    Raised when legacy scoring is invoked at runtime.
    Only active when ONLY_PIPELINE_CAN_SCORE is True.
    """
    pass


def assert_no_legacy_scoring():
    """
    Runtime guard: ensures legacy scoring modules are not importable.
    Call at startup to fail fast if old code paths remain.
    """
    for mod in FORBIDDEN_IMPORTS:
        if mod in __import__("sys").modules:
            raise ScoringViolationError(
                f"Legacy scoring module loaded: {mod}. "
                f"Use {SOURCE_OF_TRUTH} instead."
            )
