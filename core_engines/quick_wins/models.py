from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuickWin:
    endpoint_path: str
    endpoint_method: str
    quick_win_score: float
    roi_score: float
    confidence_score: float
    exploitability_score: float
    complexity_score: float
    category: str
    reasoning: str
    supporting_signals: list[str] = field(default_factory=list)
    estimated_payout: float = 0.0
    estimated_effort_minutes: int = 0
    verdict_status: str | None = None
    verdict_confidence: float | None = None
    evidence_count: int = 0
    reproducibility_score: float | None = None


@dataclass(frozen=True)
class FastExploitPath:
    entry_endpoint: str
    entry_method: str
    chain_length: int
    vulnerability_type: str
    payout_likelihood: float
    evidence_steps: list[str]
    impact_summary: str
    path_id: str = ""


@dataclass(frozen=True)
class LowEffortHighRoi:
    target_name: str
    endpoint_path: str
    endpoint_method: str
    roi_score: float
    complexity_score: float
    effort_estimate_minutes: int
    reason: str
    is_partially_confirmed: bool = False
    is_underexplored: bool = False


@dataclass(frozen=True)
class ImmediateActionEndpoint:
    path: str
    method: str
    action: str
    priority: str
    confidence: float
    risk_score: float
    reason: str
    steps: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class QuickWinsReport:
    generated_at: str
    target_name: str

    top_quick_wins: list[QuickWin] = field(default_factory=list)
    fast_exploit_paths: list[FastExploitPath] = field(default_factory=list)
    low_effort_high_roi_targets: list[LowEffortHighRoi] = field(default_factory=list)
    immediate_action_endpoints: list[ImmediateActionEndpoint] = field(default_factory=list)
    confidence_ranked_opportunities: list[QuickWin] = field(default_factory=list)

    total_opportunities: int = 0
    avg_quick_win_score: float = 0.0
    exploitability_score: float = 0.0
    fastest_path_minutes: int = 0
    total_estimated_value: float = 0.0
