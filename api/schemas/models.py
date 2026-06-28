from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    skip: int = 0
    limit: int = 100


class TargetOut(BaseModel):
    id: int
    name: str
    domain: str | None = None
    created_at: str | None = None
    endpoint_count: int = 0
    finding_count: int = 0
    confirmed_findings: int = 0
    estimated_payout: int = 0
    roi: float = 0.0
    risk_score: float = 0.0
    opportunity_score: float = 0.0
    competition_score: float = 0.0
    freshness_score: float = 0.0


class TargetSummaryOut(BaseModel):
    id: int
    name: str
    domain: str | None = None
    endpoint_count: int
    finding_count: int
    confirmed_count: int
    estimated_payout: int
    roi: float
    max_risk: float
    surfaces: list[str] = []
    vectors: list[str] = []
    opportunity_score: float = 0.0
    competition_score: int = 0
    freshness_score: int = 0


class EndpointOut(BaseModel):
    id: int
    target_id: int
    path: str
    method: str = "GET"
    risk_score: float = 0.0
    confidence: float = 0.0
    vector: str = "unknown"
    labels: list[str] = []
    signals: list[str] = []
    attack_surface: list[str] = []
    actionable: bool = False


class FindingOut(BaseModel):
    id: int
    target_id: int
    endpoint_id: int | None = None
    title: str
    severity: str = "medium"
    description: str | None = None
    payout: int = 0
    target_name: str = ""
    endpoint_path: str = ""
    created_at: str | None = None


class EvidenceOut(BaseModel):
    id: int
    verdict_id: int
    endpoint_id: int | None = None
    attempt_label: str = ""
    request_url: str = ""
    request_method: str = "GET"
    response_status: int | None = None
    consistent: bool = False
    curl_command: str | None = None
    body_diff_ratio: float = 0.0
    request_body: str | None = None
    response_body: str | None = None
    request_headers: str | None = None
    response_headers: str | None = None


class OpportunityOut(BaseModel):
    target_id: int
    name: str
    domain: str = ""
    roi: float = 0.0
    max_risk: float = 0.0
    endpoint_count: int = 0
    finding_count: int = 0
    surfaces: list[str] = []
    vectors: list[str] = []
    estimated_payout: int = 0
    opportunity_score: float = 0.0
    competition_score: int = 0
    freshness_score: int = 0


class AttackSurfaceGroup(BaseModel):
    name: str
    endpoints: list[EndpointOut]


class VerdictOut(BaseModel):
    id: int
    hotspot_path_id: str | None = None
    endpoint_id: int | None = None
    status: str = "inconclusive"
    confidence: float = 0.0
    reproducibility_score: float = 0.0
    retry_count: int = 0
    reason: str | None = None
    created_at: str | None = None


class PipelineStageOut(BaseModel):
    detected: list[FindingOut] = []
    validated: list[FindingOut] = []
    confirmed: list[FindingOut] = []
    reported: list[FindingOut] = []


class HypothesisScoreOut(BaseModel):
    likelihood: float = 0.0
    impact: float = 0.0
    exploitability: float = 0.0
    confidence: float = 0.0
    priority_score: float = 0.0
    breakdown: dict[str, float] = {}


class HypothesisOut(BaseModel):
    id: str
    vulnerability_type: str
    target_id: int
    target_name: str
    endpoint: dict[str, Any] = {}
    likelihood: float = 0.0
    impact: float = 0.0
    exploitability: float = 0.0
    confidence: float = 0.0
    priority_score: float = 0.0
    roi_score: float = 0.0
    evidence: list[str] = []
    reasoning: str = ""
    suggested_actions: list[str] = []
    source: str = "rule"
    vector: str = ""
    attack_surface_labels: list[str] = []
    similarity_to_past: float = 0.0
    past_pattern_id: str | None = None
    score: HypothesisScoreOut = Field(default_factory=HypothesisScoreOut)


class HypothesisEngineOutputOut(BaseModel):
    attack_queue: list[HypothesisOut] = []
    total_hypotheses: int = 0
    by_source: dict[str, int] = {}
    by_type: dict[str, int] = {}
    top_priority: HypothesisOut | None = None
    summary: str = ""
    total_roi_value: float = 0.0
    avg_roi: float = 0.0
    max_roi: float = 0.0
    profitable_count: int = 0


class ROIDetailOut(BaseModel):
    endpoint_id: int | None = None
    hypothesis_id: str | None = None
    vulnerability_type: str = ""
    path: str = ""
    method: str = "GET"
    roi_normalized: float = 0.0
    roi_ratio: float = 0.0
    payout_estimate: float = 0.0
    time_cost_hours: float = 0.0
    expected_return: float = 0.0
    expected_cost: float = 0.0
    probability_success: float = 0.0
    priority_score: float = 0.0
    is_profitable: bool = False
    breakdown: dict[str, float] = {}


class TargetROIOut(BaseModel):
    target_id: int
    target_name: str
    total_hypotheses: int = 0
    avg_roi: float = 0.0
    max_roi: float = 0.0
    profitable_count: int = 0
    total_expected_return: float = 0.0
    total_expected_cost: float = 0.0
    highest_payout: float = 0.0
    top_opportunities: list[ROIDetailOut] = []
    all_roi: list[ROIDetailOut] = []


class ReportOut(BaseModel):
    title: str = ""
    summary: str = ""
    findings: list[FindingOut] = []
    total_findings: int = 0
    total_estimated_value: int = 0
    generated_at: str = ""
    markdown: str = ""


# ── Phase 0: Identity & Investigation schemas ──


class TargetIdentityOut(BaseModel):
    id: int
    target_id: int
    label: str
    auth_type: str
    is_baseline: bool
    is_active: bool
    session_valid: bool = False
    session_expires_at: str | None = None
    created_at: str | None = None


class TargetIdentityCreate(BaseModel):
    label: str = "Default"
    auth_type: str = "none"
    username: str | None = None
    password: str | None = None
    token: str | None = None
    api_key: str | None = None
    cookies: dict[str, str] | None = None
    login_url: str | None = None
    login_params: dict[str, Any] | None = None
    is_baseline: bool = False


class TargetIdentityUpdate(BaseModel):
    label: str | None = None
    auth_type: str | None = None
    username: str | None = None
    password: str | None = None
    token: str | None = None
    api_key: str | None = None
    cookies: dict[str, str] | None = None
    login_url: str | None = None
    login_params: dict[str, Any] | None = None
    is_baseline: bool | None = None
    is_active: bool | None = None


class TargetSessionStatus(BaseModel):
    identity_id: int
    is_valid: bool
    expires_at: str | None = None
    last_refresh_at: str | None = None
    failure_count: int = 0


class InvestigationOut(BaseModel):
    id: int
    target_id: int
    target_name: str = ""
    name: str
    status: str
    pipeline_state: dict[str, Any] = {}
    notes: str | None = None
    tags: list[str] = []
    created_at: str | None = None
    updated_at: str | None = None


class InvestigationCreate(BaseModel):
    target_id: int
    name: str
    notes: str | None = None
    tags: list[str] | None = None


class InvestigationUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class ValidationRunOut(BaseModel):
    id: int
    investigation_id: int | None = None
    endpoint_id: int
    identity_baseline_id: int | None = None
    identity_probe_id: int | None = None
    status: str
    verdict_id: int | None = None
    started_at: str | None = None
    finished_at: str | None = None


class ReportNewOut(BaseModel):
    id: int
    investigation_id: int | None = None
    format: str
    program: str = ""
    target: str = ""
    vulnerability: str = ""
    severity: str = "medium"
    status: str = "draft"
    estimated_reward: float = 0.0
    confirmed_reward: float = 0.0
    created_at: str | None = None


class ReportFullOut(BaseModel):
    id: int
    investigation_id: int | None = None
    format: str
    content: dict[str, Any] | None = None
    finding_ids: list[int] = []
    program: str = ""
    target: str = ""
    vulnerability: str = ""
    severity: str = "medium"
    status: str = "draft"
    estimated_reward: float = 0.0
    confirmed_reward: float = 0.0
    currency: str = "USD"
    evidence_count: int = 0
    notes: str = ""
    timeline: list[dict[str, Any]] = []
    attachments: list[str] = []
    created_at: str | None = None
    updated_at: str | None = None


class ReportListItem(BaseModel):
    id: int
    format: str
    summary: str = ""
    program: str = ""
    target: str = ""
    vulnerability: str = ""
    severity: str = "medium"
    status: str = "draft"
    estimated_reward: float = 0.0
    confirmed_reward: float = 0.0
    currency: str = "USD"
    evidence_count: int = 0
    finding_ids: list[int] = []
    created_at: str | None = None
    updated_at: str | None = None


class ReportUpdate(BaseModel):
    status: str | None = None
    program: str | None = None
    target: str | None = None
    vulnerability: str | None = None
    severity: str | None = None
    estimated_reward: float | None = None
    confirmed_reward: float | None = None
    currency: str | None = None
    evidence_count: int | None = None
    notes: str | None = None
    timeline: list[dict[str, Any]] | None = None
    attachments: list[str] | None = None


class ReportCreate(BaseModel):
    finding_ids: list[int]
    program: str = ""
    target: str = ""
    vulnerability: str = ""
    severity: str = "medium"
    notes: str = ""
