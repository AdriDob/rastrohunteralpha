"""Reward Learning: learns from actual report/payout history.

Adjusts per-vulnerability-type payout estimates, tracks per-program
metrics (acceptance rate, avg payout, response time), and measures
prediction accuracy over time.

Data flow:
  reports (DB) → aggregate by type → compare predicted vs actual
  → compute adjustment factors → update BASE_PAYOUT dynamically
  → provide per-program ROI intelligence
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from database.db import SessionLocal
from database.models import Report
from core_engines.engine.roi_model import BASE_PAYOUT, BASE_HOURS

LOG = logging.getLogger("rastro.intelligence.reward")


@dataclass
class VulnTypeStats:
    vulnerability_type: str
    count: int = 0
    confirmed_count: int = 0
    total_estimated: float = 0.0
    total_confirmed: float = 0.0
    avg_estimated: float = 0.0
    avg_confirmed: float = 0.0
    avg_prediction_error: float = 0.0
    base_payout: float = 0.0
    learned_payout: float = 0.0
    adjustment_factor: float = 1.0


@dataclass
class ProgramRewardMetrics:
    program: str
    report_count: int = 0
    confirmed_count: int = 0
    acceptance_rate: float = 0.0
    total_confirmed: float = 0.0
    avg_payout: float = 0.0
    highest_payout: float = 0.0
    avg_response_days: float = 0.0
    vulnerability_types: List[str] = field(default_factory=list)


@dataclass
class RewardLearningReport:
    generated_at: str = ""
    total_reports: int = 0
    total_confirmed: int = 0
    total_confirmed_value: float = 0.0
    overall_acceptance_rate: float = 0.0
    by_type: Dict[str, VulnTypeStats] = field(default_factory=dict)
    by_program: Dict[str, ProgramRewardMetrics] = field(default_factory=dict)
    top_programs_by_payout: List[Dict[str, Any]] = field(default_factory=list)
    top_programs_by_acceptance: List[Dict[str, Any]] = field(default_factory=list)
    prediction_accuracy: float = 0.0
    summary: str = ""


class RewardLearner:
    """Learns from report/payout history to improve ROI predictions."""

    def __init__(self):
        self._adjustments: Dict[str, float] = {}

    def analyze(self) -> RewardLearningReport:
        now = datetime.now(timezone.utc).isoformat()
        report = RewardLearningReport(generated_at=now)

        session = SessionLocal()
        try:
            reports = session.query(Report).all()
        finally:
            session.close()

        if not reports:
            report.summary = "No report history available for reward learning."
            return report

        report.total_reports = len(reports)
        confirmed = [r for r in reports if r.confirmed_reward and r.confirmed_reward > 0]
        report.total_confirmed = len(confirmed)
        report.total_confirmed_value = sum(r.confirmed_reward or 0 for r in confirmed)
        report.overall_acceptance_rate = round(
            report.total_confirmed / report.total_reports * 100, 2
        ) if report.total_reports else 0.0

        by_type: Dict[str, List[Report]] = defaultdict(list)
        by_program: Dict[str, List[Report]] = defaultdict(list)
        for r in reports:
            vt = (r.vulnerability or "unknown").lower()
            by_type[vt].append(r)
            program = r.program or r.target or "unknown"
            by_program[program].append(r)

        total_prediction_error = 0.0
        error_count = 0
        for vt, vt_reports in by_type.items():
            count = len(vt_reports)
            confirmed_vt = [r for r in vt_reports if r.confirmed_reward and r.confirmed_reward > 0]
            confirmed_count = len(confirmed_vt)
            total_est = sum(r.estimated_reward or 0 for r in vt_reports)
            total_conf = sum(r.confirmed_reward or 0 for r in confirmed_vt)
            avg_est = round(total_est / count, 2) if count else 0.0
            avg_conf = round(total_conf / confirmed_count, 2) if confirmed_count else 0.0

            for r in confirmed_vt:
                est = r.estimated_reward or 0
                actual = r.confirmed_reward or 0
                if est > 0:
                    error = abs(actual - est) / est
                    total_prediction_error += error
                    error_count += 1

            try:
                vt_enum = next(
                    e for e in __import__(
                        "core_engines.engine.hypothesis.models", fromlist=["VulnerabilityType"]
                    ).VulnerabilityType if e.value == vt
                )
                base = BASE_PAYOUT.get(vt_enum, 2000.0)
                base_hours = BASE_HOURS.get(vt_enum, 5.0)
            except (StopIteration, AttributeError):
                base = 2000.0
                base_hours = 5.0

            learned = base
            if confirmed_count >= 2 and avg_conf > 0:
                learned = round((base + avg_conf) / 2, 2)

            adjustment = round(learned / base, 4) if base else 1.0
            if adjustment < 0.5 or adjustment > 2.0:
                adjustment = 1.0

            self._adjustments[vt] = adjustment

            report.by_type[vt] = VulnTypeStats(
                vulnerability_type=vt,
                count=count,
                confirmed_count=confirmed_count,
                total_estimated=round(total_est, 2),
                total_confirmed=round(total_conf, 2),
                avg_estimated=avg_est,
                avg_confirmed=avg_conf,
                avg_prediction_error=round(
                    sum(abs((r.confirmed_reward or 0) - (r.estimated_reward or 0))
                        for r in confirmed_vt) / confirmed_count, 2
                ) if confirmed_count else 0.0,
                base_payout=base,
                learned_payout=learned,
                adjustment_factor=adjustment,
            )

        report.prediction_accuracy = round(
            (1.0 - (total_prediction_error / error_count)) * 100, 2
        ) if error_count else 0.0

        for program, prog_reports in by_program.items():
            confirmed_prog = [r for r in prog_reports if r.confirmed_reward and r.confirmed_reward > 0]
            confirmed_count = len(confirmed_prog)
            total_conf = sum(r.confirmed_reward or 0 for r in confirmed_prog)
            vtypes = list(set(r.vulnerability or "unknown" for r in prog_reports))

            response_times = []
            for r in confirmed_prog:
                if r.created_at and r.updated_at and r.updated_at > r.created_at:
                    delta = (r.updated_at - r.created_at).total_seconds() / 86400
                    response_times.append(delta)

            report.by_program[program] = ProgramRewardMetrics(
                program=program,
                report_count=len(prog_reports),
                confirmed_count=confirmed_count,
                acceptance_rate=round(
                    confirmed_count / len(prog_reports) * 100, 2
                ) if prog_reports else 0.0,
                total_confirmed=round(total_conf, 2),
                avg_payout=round(total_conf / confirmed_count, 2) if confirmed_count else 0.0,
                highest_payout=round(max(r.confirmed_reward or 0 for r in confirmed_prog), 2) if confirmed_prog else 0.0,
                avg_response_days=round(sum(response_times) / len(response_times), 1) if response_times else 0.0,
                vulnerability_types=sorted(vtypes),
            )

        sorted_by_payout = sorted(
            report.by_program.values(),
            key=lambda m: m.total_confirmed, reverse=True,
        )[:10]
        report.top_programs_by_payout = [
            {"program": m.program, "total_confirmed": m.total_confirmed,
             "avg_payout": m.avg_payout, "acceptance_rate": m.acceptance_rate}
            for m in sorted_by_payout
        ]

        sorted_by_acceptance = sorted(
            (m for m in report.by_program.values() if m.report_count >= 3),
            key=lambda m: m.acceptance_rate, reverse=True,
        )[:10]
        report.top_programs_by_acceptance = [
            {"program": m.program, "acceptance_rate": m.acceptance_rate,
             "confirmed_count": m.confirmed_count, "avg_payout": m.avg_payout}
            for m in sorted_by_acceptance
        ]

        report.summary = self._build_summary(report)
        return report

    def get_adjustment(self, vulnerability_type: str) -> float:
        return self._adjustments.get(vulnerability_type.lower(), 1.0)

    def get_adjustments(self) -> Dict[str, float]:
        return dict(self._adjustments)

    def _build_summary(self, report: RewardLearningReport) -> str:
        parts = []
        parts.append(f"Reports analyzed: {report.total_reports}")
        parts.append(f"Confirmed: {report.total_confirmed} ({report.overall_acceptance_rate}%)")
        parts.append(f"Total confirmed value: ${report.total_confirmed_value:,.2f}")
        parts.append(f"Prediction accuracy: {report.prediction_accuracy}%")

        if report.by_type:
            best_learned = min(
                (s for s in report.by_type.values() if s.confirmed_count >= 2),
                key=lambda s: abs(s.adjustment_factor - 1.0),
                default=None,
            )
            if best_learned:
                parts.append(
                    f"Best calibrated type: {best_learned.vulnerability_type} "
                    f"(adj: {best_learned.adjustment_factor}x, "
                    f"base=${best_learned.base_payout:.0f} → "
                    f"learned=${best_learned.learned_payout:.0f})"
                )

        if report.top_programs_by_payout:
            top = report.top_programs_by_payout[0]
            parts.append(
                f"Top program by payout: {top['program']} "
                f"(${top['total_confirmed']:,.2f})"
            )

        return " | ".join(parts) if parts else "No reward learning data available."
