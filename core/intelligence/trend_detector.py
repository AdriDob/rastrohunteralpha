import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.db import SessionLocal

LOG = logging.getLogger("rastro.intelligence.trends")


@dataclass
class TrendSignal:
    label: str
    dimension: str
    direction: str
    current_value: float
    previous_value: float
    change_pct: float
    confidence: float
    sample_size: int
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["change_pct"] = round(d["change_pct"], 1)
        d["current_value"] = round(d["current_value"], 2)
        d["previous_value"] = round(d["previous_value"], 2)
        d["confidence"] = round(d["confidence"], 4)
        return d


@dataclass
class TrendReport:
    rising_surfaces: List[TrendSignal] = field(default_factory=list)
    emerging_vulnerability_classes: List[TrendSignal] = field(default_factory=list)
    growing_target_categories: List[TrendSignal] = field(default_factory=list)
    repeated_endpoint_patterns: List[TrendSignal] = field(default_factory=list)
    declining_trends: List[TrendSignal] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rising_surfaces": [s.to_dict() for s in self.rising_surfaces],
            "emerging_vulnerability_classes": [s.to_dict() for s in self.emerging_vulnerability_classes],
            "growing_target_categories": [s.to_dict() for s in self.growing_target_categories],
            "repeated_endpoint_patterns": [s.to_dict() for s in self.repeated_endpoint_patterns],
            "declining_trends": [s.to_dict() for s in self.declining_trends],
            "generated_at": self.generated_at,
        }


def detect_trends(
    registry: Any = None,
    history: Any = None,
) -> TrendReport:
    session = SessionLocal()
    try:
        from database.models import Finding, Verdict, Endpoint, Target
        from sqlalchemy import func

        report = TrendReport()

        # Rising attack surfaces: group endpoints by labels/attack_surface
        endpoints = session.query(Endpoint).all()
        surface_counts: Dict[str, int] = {}
        for ep in endpoints:
            params = ep.parsed_params if hasattr(ep, 'parsed_params') else {}
            surfaces = params.get("attack_surface", []) if isinstance(params, dict) else []
            if isinstance(surfaces, list):
                for s in surfaces:
                    surface_counts[s] = surface_counts.get(s, 0) + 1

        total_eps = len(endpoints) or 1
        sorted_surfaces = sorted(surface_counts.items(), key=lambda x: x[1], reverse=True)
        for surface, count in sorted_surfaces[:8]:
            pct = round(count / total_eps * 100, 1)
            report.rising_surfaces.append(TrendSignal(
                label=surface,
                dimension="attack_surface",
                direction="active",
                current_value=pct,
                previous_value=0.0,
                change_pct=pct,
                confidence=round(min(pct / 100, 0.9), 3),
                sample_size=count,
            ))

        # Emerging vulnerability classes from finding titles
        findings = session.query(Finding).all()
        vuln_counter: Dict[str, int] = {}
        for f in findings:
            vtype = f.title.split(":")[0] if ":" in f.title else f.title.split()[0] if f.title else "unknown"
            vuln_counter[vtype] = vuln_counter.get(vtype, 0) + 1

        total_findings = len(findings) or 1
        sorted_vulns = sorted(vuln_counter.items(), key=lambda x: x[1], reverse=True)
        for vtype, count in sorted_vulns[:8]:
            pct = round(count / total_findings * 100, 1)
            confidence = min(0.5 + (count / total_findings), 0.95)
            report.emerging_vulnerability_classes.append(TrendSignal(
                label=vtype,
                dimension="vulnerability_type",
                direction="rising",
                current_value=pct,
                previous_value=0.0,
                change_pct=pct,
                confidence=round(confidence, 3),
                sample_size=count,
            ))

        # Repeated endpoint patterns: analyze path patterns
        path_patterns: Dict[str, int] = {}
        import re
        for ep in endpoints:
            path = ep.path or "/"
            parts = [p for p in path.split("/") if p and not p.isdigit() and not re.match(r'^\{.*\}$', p)]
            if len(parts) >= 2:
                pattern = "/" + "/".join(parts[:2])
                path_patterns[pattern] = path_patterns.get(pattern, 0) + 1

        sorted_paths = sorted(path_patterns.items(), key=lambda x: x[1], reverse=True)
        for pattern, count in sorted_paths[:5]:
            if count >= 2:
                report.repeated_endpoint_patterns.append(TrendSignal(
                    label=pattern,
                    dimension="endpoint_path",
                    direction="repeated",
                    current_value=float(count),
                    previous_value=0.0,
                    change_pct=100.0,
                    confidence=round(min(count / total_eps * 2, 0.95), 3),
                    sample_size=count,
                ))

        # Growing target categories from target domains
        targets = session.query(Target).all()
        domain_tlds: Dict[str, int] = {}
        for t in targets:
            if t.domain and "." in t.domain:
                tld = t.domain.rsplit(".", 1)[-1]
                domain_tlds[tld] = domain_tlds.get(tld, 0) + 1

        total_targets = len(targets) or 1
        for tld, count in sorted(domain_tlds.items(), key=lambda x: x[1], reverse=True)[:5]:
            pct = round(count / total_targets * 100, 1)
            report.growing_target_categories.append(TrendSignal(
                label=tld,
                dimension="target_category",
                direction="growing",
                current_value=pct,
                previous_value=0.0,
                change_pct=pct,
                confidence=round(min(0.5 + pct / 200, 0.9), 3),
                sample_size=count,
            ))

        return report

    finally:
        session.close()
