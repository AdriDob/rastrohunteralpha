import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from database.db import SessionLocal

LOG = logging.getLogger("rastro.intelligence.snapshots")


@dataclass(frozen=True)
class LearningSnapshot:
    snapshot_type: str
    period_start: str
    period_end: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    total_targets: int = 0
    total_endpoints: int = 0
    total_findings: int = 0
    total_verdicts: int = 0
    confirmed_verdicts: int = 0
    rejected_verdicts: int = 0
    total_payout: float = 0.0
    acceptance_rate: float = 0.0
    duplicate_rate: float = 0.0
    avg_payout: float = 0.0
    avg_confidence: float = 0.0
    new_targets_count: int = 0
    new_findings_count: int = 0
    new_verdicts_count: int = 0

    top_vulnerability_types: list[dict[str, Any]] = field(default_factory=list)
    top_platforms: list[dict[str, Any]] = field(default_factory=list)
    top_patterns: list[dict[str, Any]] = field(default_factory=list)
    top_targets: list[dict[str, Any]] = field(default_factory=list)

    roi_metrics: dict[str, float] = field(default_factory=lambda: {
        "total_roi": 0.0, "avg_roi": 0.0, "max_roi": 0.0, "high_value_targets": 0.0
    })
    acceptance_metrics: dict[str, float] = field(default_factory=lambda: {
        "overall": 0.0, "critical": 0.0, "high": 0.0, "medium": 0.0, "low": 0.0
    })
    duplicate_metrics: dict[str, float] = field(default_factory=lambda: {
        "overall": 0.0, "by_severity": 0.0
    })

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_type": self.snapshot_type,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "generated_at": self.generated_at,
            "total_targets": self.total_targets,
            "total_endpoints": self.total_endpoints,
            "total_findings": self.total_findings,
            "total_verdicts": self.total_verdicts,
            "confirmed_verdicts": self.confirmed_verdicts,
            "rejected_verdicts": self.rejected_verdicts,
            "total_payout": round(self.total_payout, 2),
            "acceptance_rate": self.acceptance_rate,
            "duplicate_rate": self.duplicate_rate,
            "avg_payout": round(self.avg_payout, 2),
            "avg_confidence": round(self.avg_confidence, 4),
            "new_targets_count": self.new_targets_count,
            "new_findings_count": self.new_findings_count,
            "new_verdicts_count": self.new_verdicts_count,
            "top_vulnerability_types": self.top_vulnerability_types[:10],
            "top_platforms": self.top_platforms[:10],
            "top_patterns": self.top_patterns[:10],
            "top_targets": self.top_targets[:10],
            "roi_metrics": {k: round(v, 2) for k, v in self.roi_metrics.items()},
            "acceptance_metrics": {k: round(v, 4) for k, v in self.acceptance_metrics.items()},
            "duplicate_metrics": {k: round(v, 4) for k, v in self.duplicate_metrics.items()},
        }


def generate_snapshot(snapshot_type: str = "daily") -> LearningSnapshot:
    session = SessionLocal()
    try:
        from datetime import timedelta

        from database.models import Endpoint, Finding, Target, Verdict

        now = datetime.now(timezone.utc)

        if snapshot_type == "daily":
            delta = timedelta(days=1)
        elif snapshot_type == "weekly":
            delta = timedelta(weeks=1)
        elif snapshot_type == "monthly":
            delta = timedelta(days=30)
        else:
            delta = timedelta(days=1)

        period_start = (now - delta).isoformat()
        period_end = now.isoformat()

        all_targets = session.query(Target).all()
        all_endpoints = session.query(Endpoint).all()
        all_findings = session.query(Finding).all()
        all_verdicts = session.query(Verdict).all()

        new_targets = [t for t in all_targets if t.created_at and (now - t.created_at).total_seconds() <= delta.total_seconds()] if all_targets else []
        new_findings = [f for f in all_findings if f.created_at and (now - f.created_at).total_seconds() <= delta.total_seconds()] if all_findings else []
        new_verdicts = [v for v in all_verdicts if v.created_at and (now - v.created_at).total_seconds() <= delta.total_seconds()] if all_verdicts else []

        confirmed = [v for v in all_verdicts if v.status == "confirmed"]
        rejected = [v for v in all_verdicts if v.status == "rejected"]

        total_payout = 0.0
        for f in all_findings:
            total_payout += _severity_payout(f.severity)

        total_verdict_count = len(all_verdicts) or 1
        acceptance_rate = round(len(confirmed) / total_verdict_count, 4)

        avg_payout = round(total_payout / len(all_findings), 2) if all_findings else 0.0

        avg_confidence = 0.0
        conf_sum = 0.0
        conf_count = 0
        for v in all_verdicts:
            if v.confidence:
                try:
                    conf_sum += float(v.confidence)
                    conf_count += 1
                except (ValueError, TypeError):
                    LOG.warning("Failed to parse confidence value for snapshot", exc_info=True)
        avg_confidence = round(conf_sum / conf_count, 4) if conf_count else 0.0

        # Top vulnerability types
        from collections import Counter
        type_counter: Counter = Counter()
        for f in all_findings:
            vtype = f.title.split(":")[0] if ":" in f.title else f.title.split()[0] if f.title else "unknown"
            type_counter[vtype] += 1
        top_types = [{"type": k, "count": v} for k, v in type_counter.most_common(10)]

        # Top targets
        target_findings: dict[int, int] = {}
        for f in all_findings:
            target_findings[f.target_id] = target_findings.get(f.target_id, 0) + 1
        target_map = {t.id: t.name for t in all_targets}
        top_targets_list = [
            {"target_id": tid, "name": target_map.get(tid, f"target_{tid}"), "findings": cnt}
            for tid, cnt in sorted(target_findings.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Top patterns from endpoint paths
        import re
        path_patterns: Counter = Counter()
        for ep in all_endpoints:
            path = ep.path or "/"
            parts = [p for p in path.split("/") if p and not p.isdigit() and not re.match(r'^\{.*\}$', p)]
            if len(parts) >= 2:
                pattern = "/" + "/".join(parts[:2])
                path_patterns[pattern] += 1
        top_patterns = [{"pattern": k, "count": v} for k, v in path_patterns.most_common(10)]

        # Acceptance by severity
        Counter()
        severity_total: Counter = Counter()
        for _ in confirmed:
            severity_total["confirmed"] += 1
        for _ in rejected:
            severity_total["rejected"] += 1

        severity_acceptance = {}
        for sev in ["critical", "high", "medium", "low"]:
            total_sev = sum(1 for f in all_findings if f.severity == sev)
            conf_sev = sum(1 for f in all_findings if f.severity == sev and f.severity in ("high", "critical"))
            severity_acceptance[sev] = round(conf_sev / total_sev, 4) if total_sev else 0.0

        return LearningSnapshot(
            snapshot_type=snapshot_type,
            period_start=period_start,
            period_end=period_end,
            total_targets=len(all_targets),
            total_endpoints=len(all_endpoints),
            total_findings=len(all_findings),
            total_verdicts=len(all_verdicts),
            confirmed_verdicts=len(confirmed),
            rejected_verdicts=len(rejected),
            total_payout=total_payout,
            acceptance_rate=acceptance_rate,
            avg_payout=avg_payout,
            avg_confidence=avg_confidence,
            new_targets_count=len(new_targets),
            new_findings_count=len(new_findings),
            new_verdicts_count=len(new_verdicts),
            top_vulnerability_types=top_types,
            top_targets=top_targets_list,
            top_patterns=top_patterns,
            top_platforms=[],
            acceptance_metrics={
                "overall": acceptance_rate,
                "critical": severity_acceptance.get("critical", 0),
                "high": severity_acceptance.get("high", 0),
                "medium": severity_acceptance.get("medium", 0),
                "low": severity_acceptance.get("low", 0),
            },
            roi_metrics={
                "total_roi": total_payout,
                "avg_roi": avg_payout,
                "max_roi": round(max((_severity_payout(f.severity) for f in all_findings), default=0), 2),
                "high_value_targets": float(len([f for f in all_findings if f.severity in ("high", "critical")])),
            },
            duplicate_metrics={
                "overall": 0.0,
                "by_severity": 0.0,
            },
        )

    finally:
        session.close()


def _severity_payout(severity: str) -> float:
    severity_payout = {
        "critical": 5000.0,
        "high": 2000.0,
        "medium": 500.0,
        "low": 100.0,
        "info": 0.0,
    }
    return severity_payout.get(severity, 0.0)
