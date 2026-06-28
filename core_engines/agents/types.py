"""Agent event types — typed payloads for every agent communication."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

# ── Enums ─────────────────────────────────────────────────────────


class AgentId(str, Enum):
    COORDINATOR = "coordinator"
    RESEARCH = "research"
    VALIDATOR = "validator"
    EXPLOIT = "exploit"
    DOCUMENTATION = "documentation"
    STRATEGY = "strategy"
    MEMORY = "memory"
    FINANCIAL = "financial"


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


class EventType(str, Enum):
    # Coordination
    PIPELINE_START = "pipeline.start"
    PIPELINE_STAGE_COMPLETED = "pipeline.stage_completed"
    PIPELINE_FAILED = "pipeline.failed"
    PIPELINE_CANCELLED = "pipeline.cancelled"

    # Research
    RESEARCH_START = "research.start"
    RESEARCH_COMPLETED = "research.completed"
    RESEARCH_FAILED = "research.failed"
    TARGET_DISCOVERED = "target.discovered"
    ENDPOINT_DISCOVERED = "endpoint.discovered"

    # Validation
    VALIDATION_REQUESTED = "validation.requested"
    VALIDATION_COMPLETED = "validation.completed"
    VALIDATION_FAILED = "validation.failed"

    # Exploit
    EXPLOIT_REQUESTED = "exploit.requested"
    EXPLOIT_COMPLETED = "exploit.completed"
    EXPLOIT_FAILED = "exploit.failed"
    EXPLOIT_CONFIRMED = "exploit.confirmed"

    # Evidence
    EVIDENCE_COLLECTED = "evidence.collected"
    EVIDENCE_FAILED = "evidence.failed"

    # Documentation
    DOCUMENTATION_REQUESTED = "documentation.requested"
    DOCUMENTATION_COMPLETED = "documentation.completed"
    DOCUMENTATION_FAILED = "documentation.failed"

    # AI Review
    AI_REVIEW_REQUESTED = "ai_review.requested"
    AI_REVIEW_COMPLETED = "ai_review.completed"
    AI_REVIEW_FAILED = "ai_review.failed"

    # Submission
    SUBMISSION_REQUESTED = "submission.requested"
    SUBMISSION_COMPLETED = "submission.completed"
    SUBMISSION_FAILED = "submission.failed"

    # Strategy
    STRATEGY_RECOMMENDATION = "strategy.recommendation"
    STRATEGY_PRIORITY_UPDATED = "strategy.priority_updated"

    # Memory
    MEMORY_STORE = "memory.store"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_LEARNED = "memory.learned"

    # Financial
    FINANCIAL_UPDATED = "financial.updated"
    FINANCIAL_PAYOUT_RECORDED = "financial.payout_recorded"
    FINANCIAL_GOAL_UPDATED = "financial.goal_updated"

    # Agent lifecycle
    AGENT_HEALTH_CHANGED = "agent.health_changed"
    AGENT_REGISTERED = "agent.registered"
    AGENT_TASK_COMPLETED = "agent.task_completed"

    # System
    SYSTEM_ALERT = "system.alert"
    SYSTEM_ERROR = "system.error"


class PipelineState(str, Enum):
    """Full 11-state lifecycle of a single pipeline run."""
    PENDING = "pending"
    DISCOVERY = "discovery"
    VALIDATION = "validation"
    EVIDENCE = "evidence"
    AI_REVIEW = "ai_review"
    READY = "ready"
    SUBMITTED = "submitted"
    TRIAGED = "triaged"
    PAID = "paid"
    CLOSED = "closed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── State machine transitions ──────────────────────────────────────

VALID_TRANSITIONS: dict[PipelineState, list[PipelineState]] = {
    PipelineState.PENDING: [PipelineState.DISCOVERY, PipelineState.CANCELLED],
    PipelineState.DISCOVERY: [PipelineState.VALIDATION, PipelineState.FAILED, PipelineState.CANCELLED],
    PipelineState.VALIDATION: [PipelineState.EVIDENCE, PipelineState.FAILED, PipelineState.CANCELLED],
    PipelineState.EVIDENCE: [PipelineState.AI_REVIEW, PipelineState.FAILED, PipelineState.CANCELLED],
    PipelineState.AI_REVIEW: [PipelineState.READY, PipelineState.FAILED, PipelineState.CANCELLED],
    PipelineState.READY: [PipelineState.SUBMITTED, PipelineState.FAILED, PipelineState.CANCELLED],
    PipelineState.SUBMITTED: [PipelineState.TRIAGED, PipelineState.FAILED, PipelineState.CANCELLED],
    PipelineState.TRIAGED: [PipelineState.PAID, PipelineState.FAILED, PipelineState.CANCELLED],
    PipelineState.PAID: [PipelineState.CLOSED, PipelineState.FAILED, PipelineState.CANCELLED],
    PipelineState.CLOSED: [],
    PipelineState.FAILED: [],
    PipelineState.CANCELLED: [],
}

PIPELINE_SEQUENCE: list[PipelineState] = [
    PipelineState.DISCOVERY,
    PipelineState.VALIDATION,
    PipelineState.EVIDENCE,
    PipelineState.AI_REVIEW,
    PipelineState.READY,
    PipelineState.SUBMITTED,
    PipelineState.TRIAGED,
    PipelineState.PAID,
    PipelineState.CLOSED,
]

PIPELINE_TERMINAL = {PipelineState.CLOSED, PipelineState.FAILED, PipelineState.CANCELLED}


def validate_transition(current: PipelineState | str, target: PipelineState | str) -> bool:
    """Check if a state transition is valid per the state machine."""
    if isinstance(current, str):
        try:
            current = PipelineState(current)
        except ValueError:
            return False
    if isinstance(target, str):
        try:
            target = PipelineState(target)
        except ValueError:
            return False
    if current == target:
        return True
    allowed = VALID_TRANSITIONS.get(current, [])
    return target in allowed


# ── Typed Payload Schemas ────────────────────────────────────────


@dataclass(frozen=True)
class ResearchCompletedPayload:
    target_id: int
    target_name: str
    endpoints_count: int
    endpoints: list[dict[str, Any]]
    pipeline_id: str = ""


@dataclass(frozen=True)
class ValidationCompletedPayload:
    target_id: int
    target_name: str
    verdicts: dict[str, Any]
    confirmed_count: int
    endpoints: list[dict[str, Any]]
    pipeline_id: str = ""


@dataclass(frozen=True)
class ExploitCompletedPayload:
    target_id: int
    target_name: str
    confirmed: dict[str, Any]
    pipeline_id: str = ""


@dataclass(frozen=True)
class DocumentationCompletedPayload:
    target_id: int
    target_name: str
    reports: list[dict[str, Any]]
    reports_count: int
    pipeline_id: str = ""


@dataclass(frozen=True)
class StrategyRecommendationPayload:
    recommendation: dict[str, Any]


@dataclass(frozen=True)
class MemoryStorePayload:
    key: str
    value: Any
    namespace: str = "general"


@dataclass(frozen=True)
class FinancialPayoutPayload:
    amount: float
    program: str
    currency: str = "USD"
    vulnerability: str = ""
    severity: str = ""
    report_id: str = ""


@dataclass(frozen=True)
class AIReviewCompletedPayload:
    target_id: int
    target_name: str
    score: float
    verdict: str
    summary: str
    pipeline_id: str = ""


@dataclass(frozen=True)
class SubmissionCompletedPayload:
    target_id: int
    target_name: str
    platform: str
    report_id: str
    external_id: str
    pipeline_id: str = ""


@dataclass(frozen=True)
class PipelineStageCompletedPayload:
    target_id: int
    target_name: str
    stage: str
    next_stage: str
    pipeline_id: str = ""


# ── Base Event ───────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentEvent:
    """Immutable envelope for every event on the bus.

    All events are frozen — once created they cannot be modified.
    Always includes event_id, timestamp, correlation_id for full traceability.
    """
    event_id: str = field(default_factory=lambda: uuid4().hex[:12])
    event_type: EventType | str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: AgentId | str = ""
    target: AgentId | str | None = None
    correlation_id: str = ""
    priority: int = 5  # 1 (highest) → 10 (lowest)
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Cannot mutate frozen dataclass in __post_init__
        # correlation_id is set at construction time
        object.__setattr__(self, "correlation_id",
                          self.correlation_id or self.event_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type if isinstance(self.event_type, str) else self.event_type.value,
            "timestamp": self.timestamp,
            "source": self.source if isinstance(self.source, str) else self.source.value,
            "target": self.target if self.target is None or isinstance(self.target, str) else self.target.value,
            "correlation_id": self.correlation_id,
            "priority": self.priority,
            "payload": self.payload,
        }


# ── Event type → priority mapping ─────────────────────────────────


EVENT_PRIORITY: dict[EventType, int] = {
    EventType.PIPELINE_START: 1,
    EventType.PIPELINE_FAILED: 1,
    EventType.PIPELINE_CANCELLED: 1,
    EventType.SYSTEM_ALERT: 1,
    EventType.SYSTEM_ERROR: 1,
    EventType.EXPLOIT_CONFIRMED: 2,
    EventType.STRATEGY_RECOMMENDATION: 3,
    EventType.DOCUMENTATION_COMPLETED: 3,
    EventType.AI_REVIEW_COMPLETED: 3,
    EventType.FINANCIAL_PAYOUT_RECORDED: 3,
    EventType.SUBMISSION_COMPLETED: 3,
    EventType.AGENT_HEALTH_CHANGED: 4,
    EventType.VALIDATION_COMPLETED: 4,
    EventType.PIPELINE_STAGE_COMPLETED: 5,
    EventType.RESEARCH_COMPLETED: 5,
    EventType.EVIDENCE_COLLECTED: 5,
    EventType.FINANCIAL_UPDATED: 5,
    EventType.MEMORY_LEARNED: 6,
    EventType.AGENT_REGISTERED: 7,
    EventType.AGENT_TASK_COMPLETED: 7,
    EventType.FINANCIAL_GOAL_UPDATED: 7,
    EventType.MEMORY_STORE: 8,
    EventType.MEMORY_RETRIEVED: 8,
}


def get_event_priority(event_type: EventType | str) -> int:
    if isinstance(event_type, EventType):
        return EVENT_PRIORITY.get(event_type, 5)
    return 5
