import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.db import SessionLocal

LOG = logging.getLogger("rastro.system_health")


@dataclass
class SystemHealthSummary:
    pipeline_latency_avg_ms: float = 0.0
    pipeline_latency_max_ms: float = 0.0
    pipeline_latency_count: int = 0

    avg_evidence_per_verdict: float = 0.0
    total_evidence: int = 0
    total_verdicts_with_evidence: int = 0

    avg_report_generation_ms: float = 0.0
    reports_generated: int = 0

    avg_verdict_confidence: float = 0.0
    verdict_confidence_samples: int = 0

    duplicate_rate: float = 0.0
    acceptance_rate: float = 0.0
    total_verdicts: int = 0
    confirmed_verdicts: int = 0
    rejected_verdicts: int = 0

    total_quick_wins: int = 0
    quick_wins_estimated_value: float = 0.0

    historical_recommendations_count: int = 0
    patterns_learned: int = 0
    snapshots_created: int = 0

    cache_hit_ratio: float = 0.0
    cache_entries: int = 0
    memory_growth_estimate_mb: float = 0.0

    total_targets: int = 0
    total_endpoints: int = 0
    total_findings: int = 0
    active_scans: int = 0

    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for k, v in asdict(self).items():
            if isinstance(v, float):
                result[k] = round(v, 4)
            else:
                result[k] = v
        return result


def collect_health() -> SystemHealthSummary:
    session = SessionLocal()
    try:
        from database.models import Target, Endpoint, Finding, Verdict, Evidence, ScanRun
        from core_engines.observability import get_metrics
        from core_engines.intelligence.adaptive_memory import get_memory

        summary = SystemHealthSummary()

        # Counts
        summary.total_targets = session.query(Target).count()
        summary.total_endpoints = session.query(Endpoint).count()
        summary.total_findings = session.query(Finding).count()

        # Verdict analysis
        summary.total_verdicts = session.query(Verdict).count()
        summary.confirmed_verdicts = session.query(Verdict).filter(Verdict.status == "confirmed").count()
        summary.rejected_verdicts = session.query(Verdict).filter(Verdict.status == "rejected").count()

        if summary.total_verdicts:
            summary.acceptance_rate = round(summary.confirmed_verdicts / summary.total_verdicts, 4)
            rejected = summary.rejected_verdicts
            summary.duplicate_rate = round(rejected / summary.total_verdicts, 4)

        # Active scans
        summary.active_scans = (
            session.query(ScanRun)
            .filter(ScanRun.status.in_(["pending", "running"]))
            .count()
        )

        # Evidence analysis
        summary.total_evidence = session.query(Evidence).count()
        verdicts_with_ev = (
            session.query(Evidence.verdict_id)
            .distinct()
            .count()
        )
        summary.total_verdicts_with_evidence = verdicts_with_ev
        if verdicts_with_ev:
            summary.avg_evidence_per_verdict = round(summary.total_evidence / verdicts_with_ev, 2)

        # Verdict confidence
        conf_sum = 0.0
        conf_count = 0
        for v in session.query(Verdict).all():
            if v.confidence:
                try:
                    conf_sum += float(v.confidence)
                    conf_count += 1
                except (ValueError, TypeError):
                    pass
        summary.verdict_confidence_samples = conf_count
        if conf_count:
            summary.avg_verdict_confidence = round(conf_sum / conf_count, 4)

        # Pipeline timing from observability
        obs_metrics = get_metrics()
        for metric_name, stats in obs_metrics.items():
            if "pipeline" in metric_name or "score" in metric_name:
                if stats["count"] > summary.pipeline_latency_count:
                    summary.pipeline_latency_count = stats["count"]
                    summary.pipeline_latency_avg_ms = stats["avg_ms"]
                    summary.pipeline_latency_max_ms = stats["max_ms"]

        # Intelligence state
        try:
            memory = get_memory()
            state = memory.get_state()
            summary.historical_recommendations_count = state.get("total_recommendations_generated", 0)
            summary.patterns_learned = state.get("total_patterns_learned", 0)
            summary.snapshots_created = state.get("total_snapshots_created", 0)
        except Exception:
            pass

        return summary

    finally:
        session.close()
