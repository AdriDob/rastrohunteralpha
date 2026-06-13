import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("rastro.confidence")

SEVERITY_WEIGHTS = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3, "info": 0.1}


@dataclass
class ConfidenceFactor:
    name: str
    value: float
    weight: float
    description: str = ""

    @property
    def contribution(self) -> float:
        return round(self.value * self.weight, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "weight": self.weight,
            "contribution": self.contribution,
            "description": self.description,
        }


@dataclass
class ConfidenceAudit:
    item_id: str
    item_type: str
    item_label: str
    overall_score: float
    factors: List[ConfidenceFactor] = field(default_factory=list)
    historical_influence: float = 0.0
    evidence_influence: float = 0.0
    roi_influence: float = 0.0
    reasoning_summary: str = ""
    audited_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "item_label": self.item_label,
            "overall_score": round(self.overall_score, 4),
            "factors": [f.to_dict() for f in self.factors],
            "historical_influence": round(self.historical_influence, 4),
            "evidence_influence": round(self.evidence_influence, 4),
            "roi_influence": round(self.roi_influence, 4),
            "reasoning_summary": self.reasoning_summary,
            "audited_at": self.audited_at,
        }


@dataclass
class ConfidenceReport:
    audits: List[ConfidenceAudit] = field(default_factory=list)
    average_confidence: float = 0.0
    total_audited: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audits": [a.to_dict() for a in self.audits],
            "average_confidence": round(self.average_confidence, 4),
            "total_audited": self.total_audited,
            "generated_at": self.generated_at,
        }


def _compute_verdict_confidence(v: Any) -> ConfidenceAudit:
    factors = []
    raw_str = v.confidence if hasattr(v, "confidence") else None

    # Base confidence from stored value
    stored_conf = 0.0
    if raw_str:
        try:
            stored_conf = float(raw_str)
        except (ValueError, TypeError):
            stored_conf = 0.0
    factors.append(ConfidenceFactor(
        name="stored_confidence",
        value=stored_conf,
        weight=0.4,
        description="Raw confidence score stored with verdict",
    ))

    # Status factor
    status = v.status if hasattr(v, "status") else "inconclusive"
    status_values = {"confirmed": 0.9, "inconclusive": 0.4, "rejected": 0.1}
    status_val = status_values.get(status, 0.3)
    factors.append(ConfidenceFactor(
        name="verdict_status",
        value=status_val,
        weight=0.3,
        description=f"Verdict status: {status}",
    ))

    # Reproducibility
    repro_str = v.reproducibility_score if hasattr(v, "reproducibility_score") else None
    repro = 0.0
    if repro_str:
        try:
            repro = float(repro_str)
        except (ValueError, TypeError):
            repro = 0.0
    factors.append(ConfidenceFactor(
        name="reproducibility",
        value=repro,
        weight=0.2,
        description="Reproducibility score across retry attempts",
    ))

    # Retry count bonus
    retries = v.retry_count if hasattr(v, "retry_count") else 0
    retry_bonus = min(retries / 5.0, 1.0)
    factors.append(ConfidenceFactor(
        name="retry_thoroughness",
        value=retry_bonus,
        weight=0.1,
        description=f"Based on {retries} retry attempts",
    ))

    overall = sum(f.contribution for f in factors)

    evidence_influence = stored_conf * 0.4
    historical_influence = status_val * 0.3
    roi_influence = repro * 0.2

    reasoning_parts = [
        f"Base confidence: {stored_conf:.2f}",
        f"Status ({status}) adds {status_val:.2f} weight",
        f"Reproducibility: {repro:.2f}",
    ]

    return ConfidenceAudit(
        item_id=str(v.id),
        item_type="verdict",
        item_label=f"Verdict #{v.id} ({v.status})",
        overall_score=overall,
        factors=factors,
        historical_influence=historical_influence,
        evidence_influence=evidence_influence,
        roi_influence=roi_influence,
        reasoning_summary="; ".join(reasoning_parts),
    )


def _compute_finding_confidence(f: Any, verdicts: List[Any]) -> ConfidenceAudit:
    factors = []

    severity_val = SEVERITY_WEIGHTS.get(f.severity if hasattr(f, "severity") else "medium", 0.5)
    factors.append(ConfidenceFactor(
        name="severity",
        value=severity_val,
        weight=0.35,
        description=f"Severity: {f.severity if hasattr(f, 'severity') else 'unknown'}",
    ))

    # Check for related verdicts
    related = [v for v in verdicts if v.endpoint_id == (f.endpoint_id if hasattr(f, 'endpoint_id') else None)]
    verdict_confidence = 0.0
    if related:
        confs = []
        for v in related:
            try:
                confs.append(float(v.confidence) if v.confidence else 0.0)
            except (ValueError, TypeError):
                pass
        verdict_confidence = sum(confs) / len(confs) if confs else 0.0

    factors.append(ConfidenceFactor(
        name="related_verdicts",
        value=verdict_confidence,
        weight=0.35,
        description=f"{len(related)} related verdict(s)",
    ))

    # Endpoint presence
    has_endpoint = 1.0 if (f.endpoint_id if hasattr(f, 'endpoint_id') else None) else 0.3
    factors.append(ConfidenceFactor(
        name="endpoint_attached",
        value=has_endpoint,
        weight=0.15,
        description="Whether finding references a specific endpoint",
    ))

    # Description presence
    has_description = 0.8 if (f.description if hasattr(f, 'description') else None) else 0.2
    factors.append(ConfidenceFactor(
        name="documentation",
        value=has_description,
        weight=0.15,
        description="Whether finding includes a description",
    ))

    overall = sum(f.contribution for f in factors)

    return ConfidenceAudit(
        item_id=str(f.id),
        item_type="finding",
        item_label=f.title if hasattr(f, 'title') else "Unknown",
        overall_score=overall,
        factors=factors,
        evidence_influence=verdict_confidence * 0.35,
        historical_influence=severity_val * 0.35,
        roi_influence=has_endpoint * 0.15,
        reasoning_summary=f"Severity {f.severity} (weight {severity_val}), {len(related)} related verdicts",
    )


def audit_verdicts(limit: int = 50) -> ConfidenceReport:
    from database.db import SessionLocal
    session = SessionLocal()
    try:
        from database.models import Verdict
        verdicts = session.query(Verdict).order_by(Verdict.created_at.desc()).limit(limit).all()
        audits = [_compute_verdict_confidence(v) for v in verdicts]
        avg = sum(a.overall_score for a in audits) / len(audits) if audits else 0.0
        return ConfidenceReport(audits=audits, average_confidence=avg, total_audited=len(audits))
    finally:
        session.close()


def audit_findings(limit: int = 50) -> ConfidenceReport:
    from database.db import SessionLocal
    session = SessionLocal()
    try:
        from database.models import Finding, Verdict
        findings = session.query(Finding).order_by(Finding.created_at.desc()).limit(limit).all()
        all_verdicts = session.query(Verdict).all()
        audits = [_compute_finding_confidence(f, all_verdicts) for f in findings]
        avg = sum(a.overall_score for a in audits) / len(audits) if audits else 0.0
        return ConfidenceReport(audits=audits, average_confidence=avg, total_audited=len(audits))
    finally:
        session.close()


def audit_single(item_type: str, item_id: int) -> Optional[ConfidenceAudit]:
    from database.db import SessionLocal
    session = SessionLocal()
    try:
        if item_type == "verdict":
            from database.models import Verdict
            v = session.query(Verdict).filter(Verdict.id == item_id).first()
            if v is None:
                return None
            return _compute_verdict_confidence(v)
        elif item_type == "finding":
            from database.models import Finding, Verdict
            f = session.query(Finding).filter(Finding.id == item_id).first()
            if f is None:
                return None
            all_verdicts = session.query(Verdict).all()
            return _compute_finding_confidence(f, all_verdicts)
        return None
    finally:
        session.close()
