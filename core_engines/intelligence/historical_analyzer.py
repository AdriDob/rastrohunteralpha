import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from database.db import SessionLocal

LOG = logging.getLogger("rastro.intelligence.history")


@dataclass
class VulnerabilityTypeSummary:
    vulnerability_type: str
    total_count: int = 0
    confirmed_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    avg_payout: float = 0.0
    avg_confidence: float = 0.0
    avg_validation_hours: float = 0.0
    acceptance_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TargetEfficiency:
    target_id: int
    target_name: str
    total_findings: int = 0
    confirmed_count: int = 0
    total_payout: float = 0.0
    avg_payout: float = 0.0
    acceptance_rate: float = 0.0
    roi_score: float = 0.0
    endpoint_count: int = 0
    surface_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlatformEfficiency:
    platform: str
    total_findings: int = 0
    confirmed_count: int = 0
    total_payout: float = 0.0
    avg_payout: float = 0.0
    acceptance_rate: float = 0.0
    avg_days_to_report: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExploitChain:
    chain: List[str]
    frequency: int = 0
    avg_payout: float = 0.0
    success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"chain": " → ".join(self.chain), "frequency": self.frequency,
                "avg_payout": self.avg_payout, "success_rate": self.success_rate}


@dataclass
class HistoricalSummary:
    total_investigations: int = 0
    total_confirmed: int = 0
    total_rejected: int = 0
    total_duplicates: int = 0
    total_payout: float = 0.0
    overall_acceptance_rate: float = 0.0
    overall_duplicate_rate: float = 0.0
    avg_payout_per_finding: float = 0.0
    avg_days_to_validate: float = 0.0
    avg_days_to_report: float = 0.0
    top_vulnerability_types: List[VulnerabilityTypeSummary] = field(default_factory=list)
    top_targets: List[TargetEfficiency] = field(default_factory=list)
    top_platforms: List[PlatformEfficiency] = field(default_factory=list)
    common_exploit_chains: List[ExploitChain] = field(default_factory=list)
    analyzed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_investigations": self.total_investigations,
            "total_confirmed": self.total_confirmed,
            "total_rejected": self.total_rejected,
            "total_duplicates": self.total_duplicates,
            "total_payout": round(self.total_payout, 2),
            "overall_acceptance_rate": self.overall_acceptance_rate,
            "overall_duplicate_rate": self.overall_duplicate_rate,
            "avg_payout_per_finding": round(self.avg_payout_per_finding, 2),
            "avg_days_to_validate": round(self.avg_days_to_validate, 2),
            "avg_days_to_report": round(self.avg_days_to_report, 2),
            "top_vulnerability_types": [v.to_dict() for v in self.top_vulnerability_types],
            "top_targets": [t.to_dict() for t in self.top_targets],
            "top_platforms": [p.to_dict() for p in self.top_platforms],
            "common_exploit_chains": [c.to_dict() for c in self.common_exploit_chains],
            "analyzed_at": self.analyzed_at,
        }


def analyze_historical_data(
    registry: Any = None,
) -> HistoricalSummary:
    session = SessionLocal()
    try:
        from database.models import Finding, Verdict, Evidence, Target

        all_findings = session.query(Finding).all()
        total_findings = len(all_findings)

        confirmed = [f for f in all_findings if f.severity in ("high", "critical")]
        rejected_findings = [f for f in all_findings if f.severity == "info"]
        duplicate_count = 0

        total_payout = 0.0
        for f in confirmed:
            try:
                total_payout += _severity_payout(f.severity)
            except Exception:
                total_payout += 0

        verdicts = session.query(Verdict).all()
        confirmed_verdicts = [v for v in verdicts if v.status == "confirmed"]
        rejected_verdicts = [v for v in verdicts if v.status == "rejected"]

        total_inv = len(verdicts) if verdicts else total_findings
        total_confirmed = len(confirmed_verdicts) + len(confirmed)
        total_rejected = len(rejected_verdicts) + len(rejected_findings)
        overall_acceptance = round(total_confirmed / total_inv, 4) if total_inv else 0.0
        overall_duplicate = round(duplicate_count / total_inv, 4) if total_inv else 0.0
        avg_payout = round(total_payout / total_confirmed, 2) if total_confirmed else 0.0

        # vulnerability type analysis
        from collections import Counter
        type_counter: Counter = Counter()
        type_confirmed: Counter = Counter()
        type_payout: Dict[str, float] = {}
        for f in all_findings:
            vtype = f.title.split(":")[0] if ":" in f.title else f.title.split()[0] if f.title else "unknown"
            type_counter[vtype] += 1
            if f in confirmed:
                type_confirmed[vtype] += 1
                type_payout[vtype] = type_payout.get(vtype, 0) + _severity_payout(f.severity)

        top_types = []
        for vtype, cnt in type_counter.most_common(10):
            conf = type_confirmed.get(vtype, 0)
            payout = type_payout.get(vtype, 0)
            top_types.append(VulnerabilityTypeSummary(
                vulnerability_type=vtype,
                total_count=cnt,
                confirmed_count=conf,
                avg_payout=round(payout / conf, 2) if conf else 0.0,
                acceptance_rate=round(conf / cnt, 4) if cnt else 0.0,
            ))

        # target analysis
        targets = session.query(Target).all()
        target_map = {t.id: t for t in targets}
        target_findings: Dict[int, List[Finding]] = defaultdict(list)
        for f in all_findings:
            target_findings[f.target_id].append(f)

        top_targets_list = []
        for tid, tfindings in target_findings.items():
            t = target_map.get(tid)
            tname = t.name if t else f"target_{tid}"
            t_confirmed = sum(1 for f in tfindings if f in confirmed)
            t_payout = sum(_severity_payout(f.severity) for f in tfindings if f in confirmed)
            top_targets_list.append(TargetEfficiency(
                target_id=tid, target_name=tname,
                total_findings=len(tfindings),
                confirmed_count=t_confirmed,
                total_payout=t_payout,
                avg_payout=round(t_payout / t_confirmed, 2) if t_confirmed else 0.0,
                acceptance_rate=round(t_confirmed / len(tfindings), 4) if tfindings else 0.0,
            ))
        top_targets_list.sort(key=lambda x: x.total_payout, reverse=True)
        top_targets_list = top_targets_list[:10]

        # exploit chains from evidence
        evidence_records = session.query(Evidence).all()
        chain_counter: Counter = Counter()
        for ev in evidence_records:
            if ev.attempt_label:
                chain_counter[ev.attempt_label] += 1
        chains = []
        for label, cnt in chain_counter.most_common(5):
            chains.append(ExploitChain(
                chain=[label], frequency=cnt,
                success_rate=0.0,
            ))

        return HistoricalSummary(
            total_investigations=total_inv,
            total_confirmed=total_confirmed,
            total_rejected=total_rejected,
            total_duplicates=duplicate_count,
            total_payout=total_payout,
            overall_acceptance_rate=overall_acceptance,
            overall_duplicate_rate=overall_duplicate,
            avg_payout_per_finding=avg_payout,
            avg_days_to_validate=0.0,
            avg_days_to_report=0.0,
            top_vulnerability_types=top_types,
            top_targets=top_targets_list,
            common_exploit_chains=chains,
        )
    finally:
        session.close()


def _severity_payout(severity: str) -> float:
    SEVERITY_PAYOUT = {
        "critical": 5000.0,
        "high": 2000.0,
        "medium": 500.0,
        "low": 100.0,
        "info": 0.0,
    }
    return SEVERITY_PAYOUT.get(severity, 0.0)


from collections import defaultdict
