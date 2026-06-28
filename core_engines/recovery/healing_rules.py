"""Healing rules — maps failure types to recovery strategies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("rastro.recovery.healing_rules")


class FailureType(str, Enum):
    EVENTBUS_STUCK = "eventbus_stuck"
    EVENTBUS_DEAD = "eventbus_dead"
    AGENT_CRASHED = "agent_crashed"
    AGENT_UNRESPONSIVE = "agent_unresponsive"
    SCHEDULER_DEAD = "scheduler_dead"
    PIPELINE_CORRUPT = "pipeline_corrupt"
    PIPELINE_STALLED = "pipeline_stalled"
    DB_LOCK = "db_lock"
    DB_CONNECTION_LOST = "db_connection_lost"
    MEMORY_LEAK = "memory_leak"
    MEMORY_CORRUPT = "memory_corrupt"
    WATCHDOG_STALLED = "watchdog_stalled"
    API_UNRESPONSIVE = "api_unresponsive"
    UNKNOWN = "unknown"


@dataclass
class HealingRule:
    failure_type: FailureType
    recovery_action: str
    description: str
    priority: int
    requires_circuit_breaker: bool = True


HEALING_RULES: list[HealingRule] = [
    HealingRule(
        FailureType.EVENTBUS_STUCK,
        "reset_event_bus",
        "Reset the system event bus singleton",
        priority=1,
    ),
    HealingRule(
        FailureType.EVENTBUS_DEAD,
        "restart_agent_bus",
        "Restart the agent communication bus",
        priority=1,
    ),
    HealingRule(
        FailureType.AGENT_CRASHED,
        "restart_agent",
        "Restart a specific crashed agent by agent_id",
        priority=1,
    ),
    HealingRule(
        FailureType.AGENT_UNRESPONSIVE,
        "restart_agent",
        "Restart an unresponsive agent",
        priority=2,
    ),
    HealingRule(
        FailureType.SCHEDULER_DEAD,
        "restart_scheduler",
        "Restart the background scan scheduler",
        priority=1,
    ),
    HealingRule(
        FailureType.PIPELINE_CORRUPT,
        "restore_last_valid_state",
        "Roll back to the last valid pipeline state from DB",
        priority=1,
    ),
    HealingRule(
        FailureType.PIPELINE_STALLED,
        "retry_pipeline",
        "Retry the stalled pipeline stage",
        priority=2,
    ),
    HealingRule(
        FailureType.DB_LOCK,
        "reopen_db_connection",
        "Reopen SQLite connection with WAL mode and busy_timeout",
        priority=1,
    ),
    HealingRule(
        FailureType.DB_CONNECTION_LOST,
        "reopen_db_connection",
        "Re-establish lost database connection",
        priority=1,
    ),
    HealingRule(
        FailureType.MEMORY_LEAK,
        "trim_memory_history",
        "Trim event/memory histories to max_history",
        priority=2,
    ),
    HealingRule(
        FailureType.MEMORY_CORRUPT,
        "reset_memory_store",
        "Reset the memory store to a clean state",
        priority=2,
    ),
    HealingRule(
        FailureType.WATCHDOG_STALLED,
        "restart_watchdog",
        "Restart the watchdog monitoring thread",
        priority=1,
    ),
    HealingRule(
        FailureType.API_UNRESPONSIVE,
        "restart_api_server",
        "Attempt to restart the API server via health endpoint",
        priority=1,
    ),
]


def get_rule(failure_type: FailureType) -> HealingRule | None:
    for rule in HEALING_RULES:
        if rule.failure_type == failure_type:
            return rule
    return None


def classify_failure(error_message: str, component: str) -> FailureType:
    """Heuristic — classify a raw error into a FailureType."""
    msg = error_message.lower()
    if "eventbus" in msg or "event bus" in msg:
        return FailureType.EVENTBUS_STUCK
    if "agent" in msg and ("crash" in msg or "dead" in msg):
        return FailureType.AGENT_CRASHED
    if "scheduler" in msg:
        return FailureType.SCHEDULER_DEAD
    if "pipeline" in msg and ("corrupt" in msg or "invalid" in msg):
        return FailureType.PIPELINE_CORRUPT
    if "db" in msg or "database" in msg or "sqlite" in msg or "lock" in msg:
        return FailureType.DB_LOCK
    if "memory" in msg or "leak" in msg:
        return FailureType.MEMORY_LEAK
    if "watchdog" in msg:
        return FailureType.WATCHDOG_STALLED
    if "api" in msg and ("timeout" in msg or "unreachable" in msg):
        return FailureType.API_UNRESPONSIVE
    return FailureType.UNKNOWN
