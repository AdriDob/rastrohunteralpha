from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    skip: int = 0
    limit: int = 100


class TargetOut(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    created_at: Optional[str] = None
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
    domain: Optional[str] = None
    endpoint_count: int
    finding_count: int
    confirmed_count: int
    estimated_payout: int
    roi: float
    max_risk: float
    surfaces: List[str] = []
    vectors: List[str] = []
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
    labels: List[str] = []
    signals: List[str] = []
    attack_surface: List[str] = []
    actionable: bool = False


class FindingOut(BaseModel):
    id: int
    target_id: int
    endpoint_id: Optional[int] = None
    title: str
    severity: str = "medium"
    description: Optional[str] = None
    payout: int = 0
    target_name: str = ""
    endpoint_path: str = ""
    created_at: Optional[str] = None


class EvidenceOut(BaseModel):
    id: int
    verdict_id: int
    endpoint_id: Optional[int] = None
    attempt_label: str = ""
    request_url: str = ""
    request_method: str = "GET"
    response_status: Optional[int] = None
    consistent: bool = False
    curl_command: Optional[str] = None
    body_diff_ratio: float = 0.0
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    request_headers: Optional[str] = None
    response_headers: Optional[str] = None


class OpportunityOut(BaseModel):
    target_id: int
    name: str
    domain: str = ""
    roi: float = 0.0
    max_risk: float = 0.0
    endpoint_count: int = 0
    finding_count: int = 0
    surfaces: List[str] = []
    vectors: List[str] = []
    estimated_payout: int = 0
    opportunity_score: float = 0.0
    competition_score: int = 0
    freshness_score: int = 0


class AttackSurfaceGroup(BaseModel):
    name: str
    endpoints: List[EndpointOut]


class VerdictOut(BaseModel):
    id: int
    hotspot_path_id: Optional[str] = None
    endpoint_id: Optional[int] = None
    status: str = "inconclusive"
    confidence: float = 0.0
    reproducibility_score: float = 0.0
    retry_count: int = 0
    reason: Optional[str] = None
    created_at: Optional[str] = None


class PipelineStageOut(BaseModel):
    detected: List[FindingOut] = []
    validated: List[FindingOut] = []
    confirmed: List[FindingOut] = []
    reported: List[FindingOut] = []


class HypothesisScoreOut(BaseModel):
    likelihood: float = 0.0
    impact: float = 0.0
    exploitability: float = 0.0
    confidence: float = 0.0
    priority_score: float = 0.0
    breakdown: Dict[str, float] = {}


class HypothesisOut(BaseModel):
    id: str
    vulnerability_type: str
    target_id: int
    target_name: str
    endpoint: Dict[str, Any] = {}
    likelihood: float = 0.0
    impact: float = 0.0
    exploitability: float = 0.0
    confidence: float = 0.0
    priority_score: float = 0.0
    roi_score: float = 0.0
    evidence: List[str] = []
    reasoning: str = ""
    suggested_actions: List[str] = []
    source: str = "rule"
    vector: str = ""
    attack_surface_labels: List[str] = []
    similarity_to_past: float = 0.0
    past_pattern_id: Optional[str] = None
    score: HypothesisScoreOut = Field(default_factory=HypothesisScoreOut)


class HypothesisEngineOutputOut(BaseModel):
    attack_queue: List[HypothesisOut] = []
    total_hypotheses: int = 0
    by_source: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    top_priority: Optional[HypothesisOut] = None
    summary: str = ""
    total_roi_value: float = 0.0
    avg_roi: float = 0.0
    max_roi: float = 0.0
    profitable_count: int = 0


class ROIDetailOut(BaseModel):
    endpoint_id: Optional[int] = None
    hypothesis_id: Optional[str] = None
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
    breakdown: Dict[str, float] = {}


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
    top_opportunities: List[ROIDetailOut] = []
    all_roi: List[ROIDetailOut] = []


class ReportOut(BaseModel):
    title: str = ""
    summary: str = ""
    findings: List[FindingOut] = []
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
    session_expires_at: Optional[str] = None
    created_at: Optional[str] = None


class TargetIdentityCreate(BaseModel):
    label: str = "Default"
    auth_type: str = "none"
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None
    login_url: Optional[str] = None
    login_params: Optional[Dict[str, Any]] = None
    is_baseline: bool = False


class TargetIdentityUpdate(BaseModel):
    label: Optional[str] = None
    auth_type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None
    login_url: Optional[str] = None
    login_params: Optional[Dict[str, Any]] = None
    is_baseline: Optional[bool] = None
    is_active: Optional[bool] = None


class TargetSessionStatus(BaseModel):
    identity_id: int
    is_valid: bool
    expires_at: Optional[str] = None
    last_refresh_at: Optional[str] = None
    failure_count: int = 0


class InvestigationOut(BaseModel):
    id: int
    target_id: int
    target_name: str = ""
    name: str
    status: str
    pipeline_state: Dict[str, Any] = {}
    notes: Optional[str] = None
    tags: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class InvestigationCreate(BaseModel):
    target_id: int
    name: str
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class InvestigationUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class ValidationRunOut(BaseModel):
    id: int
    investigation_id: Optional[int] = None
    endpoint_id: int
    identity_baseline_id: Optional[int] = None
    identity_probe_id: Optional[int] = None
    status: str
    verdict_id: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ReportNewOut(BaseModel):
    id: int
    investigation_id: Optional[int] = None
    format: str
    program: str = ""
    target: str = ""
    vulnerability: str = ""
    severity: str = "medium"
    status: str = "draft"
    estimated_reward: float = 0.0
    confirmed_reward: float = 0.0
    created_at: Optional[str] = None


class ReportFullOut(BaseModel):
    id: int
    investigation_id: Optional[int] = None
    format: str
    content: Optional[Dict[str, Any]] = None
    finding_ids: List[int] = []
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
    timeline: List[Dict[str, Any]] = []
    attachments: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


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
    finding_ids: List[int] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ReportUpdate(BaseModel):
    status: Optional[str] = None
    program: Optional[str] = None
    target: Optional[str] = None
    vulnerability: Optional[str] = None
    severity: Optional[str] = None
    estimated_reward: Optional[float] = None
    confirmed_reward: Optional[float] = None
    currency: Optional[str] = None
    evidence_count: Optional[int] = None
    notes: Optional[str] = None
    timeline: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[str]] = None


class ReportCreate(BaseModel):
    finding_ids: List[int]
    program: str = ""
    target: str = ""
    vulnerability: str = ""
    severity: str = "medium"
    notes: str = ""
