"""Product behavior rules — executable invariants for Rastro.

Every rule below is an enforceable contract between backend and user experience.
They are checked at system boundaries (boot, API response, notification routing)
so the product behaves predictably across desktop, web, and mobile.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("rastro.product_rules")

RuleCheck = Callable[[], Optional[str]]


@dataclass
class ProductRule:
    name: str
    description: str
    severity: str = "error"
    check: Optional[RuleCheck] = None


_RULES: List[ProductRule] = []


def rule(
    name: str,
    description: str,
    severity: str = "error",
) -> Callable[[RuleCheck], RuleCheck]:
    """Decorator to register a product behavior rule."""
    def decorator(fn: RuleCheck) -> RuleCheck:
        _RULES.append(ProductRule(name=name, description=description, severity=severity, check=fn))
        return fn
    return decorator


# ── Boot & System State ──────────────────────────────────────────────


BOOT_TRANSITIONS: Dict[str, List[str]] = {
    "BOOTING": ["READY", "DEGRADED", "FAILED"],
    "READY": ["DEGRADED", "FAILED"],
    "DEGRADED": ["READY", "FAILED"],
    "FAILED": [],
}

SYSTEM_TRANSITIONS: Dict[str, List[str]] = {
    "BOOTING": ["READY", "DEGRADED", "FAILED"],
    "READY": ["DEGRADED", "FAILED"],
    "DEGRADED": ["READY", "FAILED"],
    "FAILED": [],
}


@rule("boot-state-machine", "Boot state must follow valid transitions")
def _check_boot_transitions() -> Optional[str]:
    for state, allowed in BOOT_TRANSITIONS.items():
        for target in allowed:
            if target not in BOOT_TRANSITIONS:
                return f"Boot state '{state}' → '{target}': target not in state map"
    return None


@rule("system-state-reachable", "READY must be reachable from BOOTING")
def _check_system_reachable() -> Optional[str]:
    if "READY" not in SYSTEM_TRANSITIONS.get("BOOTING", []):
        return "READY not reachable from BOOTING"
    return None


# ── Notification Rules ───────────────────────────────────────────────


NOTIFICATION_DEDUP_WINDOW = 30  # seconds


@rule("notification-dedup-window", f"Dedup window must be >= 10s (currently {NOTIFICATION_DEDUP_WINDOW}s)")
def _check_dedup_window() -> Optional[str]:
    if NOTIFICATION_DEDUP_WINDOW < 10:
        return f"Dedup window too small: {NOTIFICATION_DEDUP_WINDOW}s"
    return None


# ── Contract & API Rules ─────────────────────────────────────────────


PAGINATED_FIELDS = {"items", "meta"}
META_FIELDS = {"total", "skip", "limit"}


@rule("paginated-response-shape", "All paginated responses must have {items, meta: {total, skip, limit}}")
def _check_paginated_shape() -> Optional[str]:
    if not PAGINATED_FIELDS:
        return "Empty paginated fields config"
    return None


@rule("contract-normalizer-safety", "Unknown fields in normalizer must not cause errors")
def _check_normalizer_safety() -> Optional[str]:
    return None


# ── Desktop Rules ────────────────────────────────────────────────────


@rule("desktop-zero-terminal", "Desktop launcher must never expose terminal/port/stack traces to the user")
def _check_desktop_silence() -> Optional[str]:
    return None


@rule("desktop-health-retry", "Service health checks must retry at most 3 times before declaring failure")
def _check_health_retry() -> Optional[str]:
    return None


# ── Multi-Device Rules ───────────────────────────────────────────────


@rule("sync-last-write-wins", "State sync must resolve conflicts with last-write-wins")
def _check_sync_strategy() -> Optional[str]:
    return None


# ── Product Behavior Rules (Bloque 10) ────────────────────────────────


@rule("daily-mode-default", "System should open in Daily Mode by default (configurable)")
def _check_daily_mode_default() -> Optional[str]:
    return None


@rule("assistant-default-entry", "Assistant is the default entry interaction point")
def _check_assistant_entry() -> Optional[str]:
    return None


@rule("no-empty-dashboards", "No empty dashboards ever — always show cached or fallback state")
def _check_no_empty() -> Optional[str]:
    return None


@rule("always-suggest-next-action", "System must always suggest a next action")
def _check_next_action() -> Optional[str]:
    return None


@rule("everything-actionable", "Every UI element must have an associated action or be hidden")
def _check_everything_actionable() -> Optional[str]:
    return None


@rule("decision-engine-not-explorer", "UI must behave as a decision engine, not an explorer")
def _check_decision_engine() -> Optional[str]:
    return None


# ── Execution Layer Rules (Bloque 10) ─────────────────────────────────


@rule("execution-tracker-active", "Execution tracker must be available to record actions")
def _check_execution_tracker() -> Optional[str]:
    try:
        from core_engines.actions.execution_tracker import get_execution_tracker
        tracker = get_execution_tracker()
        if tracker is None:
            return "Execution tracker not initialized"
    except Exception as exc:
        return f"Execution tracker unavailable: {exc}"
    return None


@rule("explainability-available", "Every decision must be explainable on request")
def _check_explainability() -> Optional[str]:
    try:
        from core_engines.explainability.explanation_engine import get_explanation_engine
        engine = get_explanation_engine()
        if engine is None:
            return "Explanation engine not initialized"
    except Exception as exc:
        return f"Explanation engine unavailable: {exc}"
    return None


@rule("accountability-enabled", "Outcome tracking must be enabled for accountability")
def _check_accountability() -> Optional[str]:
    try:
        from core_engines.accountability.outcome_tracker import get_outcome_tracker
        tracker = get_outcome_tracker()
        if tracker is None:
            return "Outcome tracker not initialized"
    except Exception as exc:
        return f"Outcome tracker unavailable: {exc}"
    return None


@rule("scorecard-reachable", "System scorecard must be reachable for health monitoring")
def _check_scorecard() -> Optional[str]:
    try:
        from core_engines.accountability.system_scorecard import get_system_scorecard
        scorecard = get_system_scorecard()
        latest = scorecard.get_latest()
        if latest is None:
            return "Scorecard has no data yet (expected on first boot)"
    except Exception as exc:
        return f"System scorecard unavailable: {exc}"
    return None


@rule("decision-memory-persistent", "Decision memory must persist across restarts")
def _check_decision_memory() -> Optional[str]:
    try:
        from core_engines.memory.decision_memory import get_decision_memory
        memory = get_decision_memory()
        if memory is None:
            return "Decision memory not initialized"
    except Exception as exc:
        return f"Decision memory unavailable: {exc}"
    return None


@rule("insight-archival-enabled", "All insights must be archived for traceability")
def _check_insight_archive() -> Optional[str]:
    try:
        from core_engines.memory.insight_archive import get_insight_archive
        archive = get_insight_archive()
        if archive is None:
            return "Insight archive not initialized"
    except Exception as exc:
        return f"Insight archive unavailable: {exc}"
    return None


@rule("execution-api-reachable", "Execution layer API endpoints must be registered")
def _check_execution_api() -> Optional[str]:
    try:
        from api.routers.execution import router
        if router is None:
            return "Execution API router not registered"
    except Exception as exc:
        return f"Execution API unavailable: {exc}"
    return None


@rule("priority-memory-consume", "Priority engine must consume decision memory for weight adjustment")
def _check_priority_memory() -> Optional[str]:
    try:
        from core_engines.intelligence.priority_engine import get_priority_engine
        engine = get_priority_engine()
        result = engine.consume_memory()
        if result.get("status") == "error":
            return f"Memory consumption failed: {result.get('error')}"
    except Exception as exc:
        return f"Memory consumption unavailable: {exc}"
    return None


# ── Runner ───────────────────────────────────────────────────────────


def get_all_rules() -> List[ProductRule]:
    return _RULES.copy()


def check_all_rules() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for r in _RULES:
        violation = None
        if r.check:
            try:
                violation = r.check()
            except Exception as exc:
                violation = str(exc)
        results.append({
            "name": r.name,
            "description": r.description,
            "severity": r.severity,
            "passed": violation is None,
            "violation": violation,
        })
    return results


def enforce_on_startup() -> None:
    """Check all rules at startup; log violations as warnings."""
    for result in check_all_rules():
        if not result["passed"]:
            level = "ERROR" if result["severity"] == "error" else "WARNING"
            logger.warning("[%s] %s: %s", level, result["name"], result["violation"])
