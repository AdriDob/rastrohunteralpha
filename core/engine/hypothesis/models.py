from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VulnerabilityType(str, Enum):
    IDOR = "idor"
    AUTH_BYPASS = "auth_bypass"
    SSRF = "ssrf"
    XSS = "xss"
    SQLI = "sqli"
    GRAPHQL_INTROSPECTION = "graphql_introspection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXPOSURE = "data_exposure"
    RATE_LIMIT_BYPASS = "rate_limit_bypass"
    WEB3_SIGNATURE_REPLAY = "web3_signature_replay"
    WEB3_RPC_LEAK = "web3_rpc_leak"
    BUSINESS_LOGIC = "business_logic"
    FILE_OPERATION = "file_operation"
    SSTI = "ssti"


class HypothesisSource(str, Enum):
    RULE = "rule"
    PATTERN = "pattern"
    LLM = "llm"


@dataclass(frozen=True)
class HypothesisScore:
    likelihood: float
    impact: float
    exploitability: float
    confidence: float
    priority_score: float
    breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Hypothesis:
    id: str
    vulnerability_type: VulnerabilityType
    target_id: int
    target_name: str
    endpoint: Dict[str, Any]
    likelihood: float
    impact: float
    exploitability: float
    confidence: float
    priority_score: float
    evidence: List[str]
    reasoning: str
    suggested_actions: List[str]
    source: HypothesisSource
    vector: str
    roi_score: float = 0.0
    attack_surface_labels: List[str] = field(default_factory=list)
    similarity_to_past: float = 0.0
    past_pattern_id: Optional[str] = None
    score: HypothesisScore = field(default_factory=lambda: HypothesisScore(0, 0, 0, 0, 0))


@dataclass
class AttackQueue:
    hypotheses: List[Hypothesis] = field(default_factory=list)
    target_id: int = 0

    def add(self, h: Hypothesis):
        self.hypotheses.append(h)

    def prioritized(self) -> List[Hypothesis]:
        return sorted(self.hypotheses, key=lambda h: (h.priority_score, h.roi_score), reverse=True)

    def top_k(self, k: int = 10) -> List[Hypothesis]:
        return self.prioritized()[:k]

    def by_type(self, vt: VulnerabilityType) -> List[Hypothesis]:
        return [h for h in self.hypotheses if h.vulnerability_type == vt]

    def count(self) -> int:
        return len(self.hypotheses)


@dataclass
class HypothesisEngineOutput:
    attack_queue: AttackQueue
    total_hypotheses: int
    by_source: Dict[str, int]
    by_type: Dict[str, int]
    top_priority: Optional[Hypothesis] = None
    summary: str = ""
    total_roi_value: float = 0.0
    avg_roi: float = 0.0
    max_roi: float = 0.0
    profitable_count: int = 0
