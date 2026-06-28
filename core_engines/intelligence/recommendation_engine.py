import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from database.db import SessionLocal

LOG = logging.getLogger("rastro.intelligence.recommendations")


@dataclass
class TargetRecommendation:
    target_id: int
    target_name: str
    domain: str
    priority_score: float
    reason: str
    evidence_count: int = 0
    finding_count: int = 0
    estimated_payout: float = 0.0
    historical_acceptance_rate: float = 0.0
    attack_surfaces: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SurfaceRecommendation:
    surface: str
    priority_score: float
    reason: str
    related_target_count: int = 0
    estimated_opportunity: float = 0.0
    trend_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuickWinRecommendation:
    target_id: int
    target_name: str
    endpoint_path: str
    endpoint_method: str
    quick_win_score: float
    estimated_payout: float
    estimated_effort_minutes: int
    reason: str
    historical_similar_success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReportRecommendation:
    finding_id: int
    title: str
    severity: str
    target_name: str
    acceptance_probability: float
    reason: str
    estimated_payout: float = 0.0
    similar_accepted_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationBundle:
    targets: list[TargetRecommendation] = field(default_factory=list)
    surfaces: list[SurfaceRecommendation] = field(default_factory=list)
    quick_wins: list[QuickWinRecommendation] = field(default_factory=list)
    reports: list[ReportRecommendation] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "targets": [t.to_dict() for t in self.targets],
            "surfaces": [s.to_dict() for s in self.surfaces],
            "quick_wins": [q.to_dict() for q in self.quick_wins],
            "reports": [r.to_dict() for r in self.reports],
            "generated_at": self.generated_at,
        }


def generate_recommendations(
    history: Any = None,
    trends: Any = None,
    registry: Any = None,
) -> RecommendationBundle:
    session = SessionLocal()
    try:
        from database.models import Endpoint, Finding, Target, Verdict

        bundle = RecommendationBundle()

        # Target recommendations
        targets = session.query(Target).all()
        verdicts = session.query(Verdict).all()
        findings = session.query(Finding).all()

        {v.id for v in verdicts if v.status == "confirmed"}
        finding_severity_map: dict[int, list[Finding]] = {}
        for f in findings:
            finding_severity_map.setdefault(f.target_id, []).append(f)

        for t in targets:
            t_findings = finding_severity_map.get(t.id, [])
            t_high = sum(1 for f in t_findings if f.severity in ("high", "critical"))
            t_total = len(t_findings)
            acceptance = round(t_high / t_total, 4) if t_total else 0.0

            if t_total >= 2 or t_high >= 1:
                payout_est = sum(_severity_payout(f.severity) for f in t_findings)
                score = round(acceptance * 10 + min(t_total * 0.5, 5) + min(payout_est / 10000, 3), 2)
                bundle.targets.append(TargetRecommendation(
                    target_id=t.id,
                    target_name=t.name,
                    domain=t.domain or "",
                    priority_score=score,
                    reason=f"{t_total} findings ({t_high} high/critical), {acceptance:.0%} acceptance",
                    finding_count=t_total,
                    estimated_payout=payout_est,
                    historical_acceptance_rate=acceptance,
                ))

        bundle.targets.sort(key=lambda x: x.priority_score, reverse=True)
        bundle.targets = bundle.targets[:10]

        # Surface recommendations from endpoint labels
        endpoints = session.query(Endpoint).all()
        surface_map: dict[str, dict[str, Any]] = {}
        for ep in endpoints:
            params = ep.parsed_params if hasattr(ep, 'parsed_params') else {}
            surfaces = params.get("attack_surface", []) if isinstance(params, dict) else []
            if isinstance(surfaces, list):
                for s in surfaces:
                    if s not in surface_map:
                        surface_map[s] = {"count": 0, "targets": set()}
                    surface_map[s]["count"] += 1
                    surface_map[s]["targets"].add(ep.target_id)

        for surface, info in sorted(surface_map.items(), key=lambda x: x[1]["count"], reverse=True)[:8]:
            bundle.surfaces.append(SurfaceRecommendation(
                surface=surface,
                priority_score=round(min(info["count"] * 0.5, 10), 2),
                reason=f"Found across {len(info['targets'])} targets ({info['count']} endpoints)",
                related_target_count=len(info["targets"]),
                trend_confidence=round(min(info["count"] / 50, 0.95), 3),
            ))

        # Quick Win recommendations: high-confidence findings with low effort
        for ep in endpoints[:20]:
            params = ep.parsed_params if hasattr(ep, 'parsed_params') else {}
            signals = params.get("signals", []) if isinstance(params, dict) else []
            if signals:
                bundle.quick_wins.append(QuickWinRecommendation(
                    target_id=ep.target_id,
                    target_name="",
                    endpoint_path=ep.path or "/",
                    endpoint_method=ep.method or "GET",
                    quick_win_score=round(min(len(signals) * 2, 10), 2),
                    estimated_payout=500.0,
                    estimated_effort_minutes=30,
                    reason=f"Signals: {', '.join(signals[:3])}",
                    historical_similar_success_rate=0.5,
                ))

        # Report recommendations: findings with highest acceptance probability
        for f in findings[:10]:
            prob = _estimate_acceptance(f.severity)
            bundle.reports.append(ReportRecommendation(
                finding_id=f.id,
                title=f.title or "Untitled",
                severity=f.severity or "medium",
                target_name="",
                acceptance_probability=prob,
                reason=f"Based on severity ({f.severity}) and historical patterns",
                estimated_payout=_severity_payout(f.severity),
                similar_accepted_count=0,
            ))

        bundle.reports.sort(key=lambda x: x.acceptance_probability, reverse=True)

        return bundle

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


def _estimate_acceptance(severity: str) -> float:
    severity_acceptance = {
        "critical": 0.85,
        "high": 0.70,
        "medium": 0.40,
        "low": 0.15,
        "info": 0.05,
    }
    return severity_acceptance.get(severity, 0.1)
