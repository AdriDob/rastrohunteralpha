import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("rastro.review_queue")


class ConfidenceTier(Enum):
    HIGH = "HIGH_CONFIDENCE"
    MEDIUM = "MEDIUM_CONFIDENCE"
    LOW = "LOW_CONFIDENCE"

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceTier":
        if score >= 0.7:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        return cls.LOW


@dataclass
class ReviewItem:
    item_id: str
    item_type: str
    label: str
    tier: str
    confidence_score: float
    reason: str
    factors: List[Dict[str, Any]] = field(default_factory=list)
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewQueue:
    high_confidence: List[ReviewItem] = field(default_factory=list)
    medium_confidence: List[ReviewItem] = field(default_factory=list)
    low_confidence: List[ReviewItem] = field(default_factory=list)
    total_items: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add(self, item: ReviewItem) -> None:
        if item.tier == "HIGH_CONFIDENCE":
            self.high_confidence.append(item)
        elif item.tier == "MEDIUM_CONFIDENCE":
            self.medium_confidence.append(item)
        else:
            self.low_confidence.append(item)
        self.total_items += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "high_confidence": [i.to_dict() for i in self.high_confidence],
            "medium_confidence": [i.to_dict() for i in self.medium_confidence],
            "low_confidence": [i.to_dict() for i in self.low_confidence],
            "total_items": self.total_items,
            "counts": {
                "high": len(self.high_confidence),
                "medium": len(self.medium_confidence),
                "low": len(self.low_confidence),
            },
            "generated_at": self.generated_at,
        }


def _classify_tier(score: float) -> str:
    return ConfidenceTier.from_score(score).value


def _build_reason(tier: str, score: float, factors: List[Dict[str, Any]]) -> str:
    if tier == "HIGH_CONFIDENCE":
        return f"Strong confidence ({score:.2f}) — reliable signal, ready for human review"
    elif tier == "MEDIUM_CONFIDENCE":
        return f"Moderate confidence ({score:.2f}) — requires human assessment"
    return f"Low confidence ({score:.2f}) — needs additional validation before review"


def build_review_queue(limit: int = 100) -> ReviewQueue:
    from database.db import SessionLocal
    session = SessionLocal()
    try:
        from database.models import Verdict, Finding, Target

        queue = ReviewQueue()

        # Verdict review items
        verdicts = session.query(Verdict).order_by(Verdict.created_at.desc()).limit(limit).all()
        for v in verdicts:
            raw_conf = 0.0
            if v.confidence:
                try:
                    raw_conf = float(v.confidence)
                except (ValueError, TypeError):
                    pass

            status = v.status or "inconclusive"
            status_bonus = {"confirmed": 0.2, "inconclusive": 0.0, "rejected": -0.1}
            adjusted = raw_conf + status_bonus.get(status, 0.0)
            adjusted = max(0.0, min(1.0, adjusted))

            factors = [
                {"name": "stored_confidence", "value": round(raw_conf, 4), "description": "Raw confidence from validation"},
                {"name": "status", "value": status, "description": f"Verdict status: {status}"},
                {"name": "retry_count", "value": v.retry_count, "description": f"Retry attempts: {v.retry_count}"},
            ]

            tier = _classify_tier(adjusted)
            reason = _build_reason(tier, adjusted, factors)

            target_name = ""
            if v.endpoint_id:
                ep = session.query(type('EP', (), {'target_id': 0})()).from_statement(
                    type('stmt', (), {})()
                )
                from database.models import Endpoint
                ep = session.query(Endpoint).filter(Endpoint.id == v.endpoint_id).first()
                if ep:
                    t = session.query(Target).filter(Target.id == ep.target_id).first()
                    if t:
                        target_name = t.name

            queue.add(ReviewItem(
                item_id=f"verdict_{v.id}",
                item_type="verdict",
                label=f"Verdict #{v.id} — {status}",
                tier=tier,
                confidence_score=round(adjusted, 4),
                reason=reason,
                factors=factors,
                target_id=v.endpoint_id,
                target_name=target_name,
                created_at=v.created_at.isoformat() if v.created_at else None,
            ))

        # High-severity finding review items
        findings = (
            session.query(Finding)
            .filter(Finding.severity.in_(["critical", "high"]))
            .order_by(Finding.created_at.desc())
            .limit(limit)
            .all()
        )
        for f in findings:
            severity_bonus = {"critical": 0.8, "high": 0.6, "medium": 0.4, "low": 0.2}
            score = severity_bonus.get(f.severity, 0.3)

            factors = [
                {"name": "severity", "value": f.severity, "description": f"Severity: {f.severity}"},
                {"name": "has_endpoint", "value": f.endpoint_id is not None, "description": "Linked to endpoint"},
            ]

            if f.endpoint_id:
                from database.models import Verdict as VerdictModel
                related = (
                    session.query(VerdictModel)
                    .filter(VerdictModel.endpoint_id == f.endpoint_id)
                    .count()
                )
                if related > 0:
                    score = min(score + 0.15, 1.0)
                    factors.append({"name": "verified", "value": related, "description": f"{related} related verdict(s)"})

            tier = _classify_tier(score)
            reason = _build_reason(tier, score, factors)

            target_name = ""
            t = session.query(Target).filter(Target.id == f.target_id).first()
            if t:
                target_name = t.name

            queue.add(ReviewItem(
                item_id=f"finding_{f.id}",
                item_type="finding",
                label=f.finding_title if hasattr(f, 'finding_title') and f.finding_title else (f.title or "Untitled"),
                tier=tier,
                confidence_score=round(score, 4),
                reason=reason,
                factors=factors,
                target_id=f.target_id,
                target_name=target_name,
                created_at=f.created_at.isoformat() if f.created_at else None,
            ))

        return queue

    finally:
        session.close()
