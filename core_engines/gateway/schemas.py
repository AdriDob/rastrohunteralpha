"""Unified data contracts (DTOs) for all API responses.

Every DTO follows:
  - version: schema version number
  - Consistent null handling (null fields omitted via exclude_none)
  - Predictable naming (snake_case)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Envelope ──────────────────────────────────────────────────────────

class APIEnvelope(BaseModel):
    """Standard API response wrapper. Every endpoint returns this shape."""
    version: str = "1.0"
    schema_: str = Field("rastro/v1", alias="schema")
    data: Any = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat() + "Z"},
    )


class PaginatedEnvelope(BaseModel):
    """Paginated response wrapper."""
    version: str = "1.0"
    schema_: str = Field("rastro/v1", alias="schema")
    items: List[Any] = []
    total: int = 0
    skip: int = 0
    limit: int = 100
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    model_config = ConfigDict(populate_by_name=True)


# ── Unified helpers ──────────────────────────────────────────────────

def ok(data: Any, version: str = "1.0") -> APIEnvelope:
    return APIEnvelope(version=version, data=data)


def error(msg: str, version: str = "1.0") -> APIEnvelope:
    return APIEnvelope(version=version, error=msg)


def paginated(items: list, total: int, skip: int = 0, limit: int = 100, version: str = "1.0") -> PaginatedEnvelope:
    return PaginatedEnvelope(version=version, items=items, total=total, skip=skip, limit=limit)


# ── Simple envelope helpers for direct dict responses ──────────────

def safe_response(data: Optional[dict] = None) -> dict:
    """Wrap a response dict with a minimal safety envelope.

    Ensures every response has 'status', 'items', 'meta', 'error' keys
    so frontend code can safely destructure without null guards.
    """
    if data is None:
        return {"status": "ok", "items": [], "meta": {}, "error": None}
    result = {"status": "ok", "items": [], "meta": {}, "error": None}
    result.update(data)
    return result


def error_response(msg: str) -> dict:
    return {"status": "error", "items": [], "meta": {}, "error": msg}


# ── DTOs ──────────────────────────────────────────────────────────────

class TargetDTO(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    endpoint_count: int = 0
    finding_count: int = 0
    confirmed_findings: int = 0
    estimated_payout: int = 0
    roi: float = 0.0
    opportunity_score: float = 0.0
    competition_score: float = 0.0
    freshness_score: float = 0.0


class OpportunityDTO(BaseModel):
    id: int
    name: str
    category: str = "general"
    source: str = "unknown"
    score: float = 0.0
    priority: str = "medium"
    estimated_payout: int = 0
    confidence: float = 0.0
    evh_value: Optional[float] = None
    evh_rating: Optional[str] = None
    public_url: Optional[str] = None
    reasoning: List[str] = []


class FindingDTO(BaseModel):
    id: int
    target_id: int
    title: str
    severity: str = "info"
    confidence: float = 0.0
    status: str = "open"
    estimated_payout: int = 0
    created_at: Optional[str] = None
    vector: Optional[str] = None


class InsightDTO(BaseModel):
    id: str
    type: str = "insight"
    title: str
    description: str
    severity: str = "info"
    source: str = "system"


class NotificationDTO(BaseModel):
    id: int
    type: str
    message: str
    is_read: bool = False
    created_at: str
    metadata: Dict[str, Any] = {}


class AssistantMessageDTO(BaseModel):
    role: str = "assistant"
    content: str
    actions: List[str] = []
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


class SyncStateDTO(BaseModel):
    device_id: str
    last_sync: str
    state: Dict[str, Any] = {}
    version: int = 1
