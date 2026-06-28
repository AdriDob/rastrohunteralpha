"""
Bug Bounty Intelligence: tracks program trends, severity changes,
scope modifications, and aggregated metrics for H1, BC, and other platforms.
Integrates with existing Hunter + Opportunity infrastructure.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core_engines.targets.models import TargetIntel
from database.db import SessionLocal

LOG = logging.getLogger("rastro.intelligence.bounty")


@dataclass
class ProgramMetrics:
    platform: str
    total_programs: int = 0
    active_programs: int = 0
    avg_quality: float = 0.0
    avg_roi: float = 0.0
    technology_breakdown: dict[str, int] = field(default_factory=dict)
    top_technologies: list[str] = field(default_factory=list)


@dataclass
class BountyIntelReport:
    generated_at: str = ""
    platform_metrics: dict[str, ProgramMetrics] = field(default_factory=dict)
    total_programs: int = 0
    total_active: int = 0
    top_programs_by_quality: list[dict[str, Any]] = field(default_factory=list)
    top_programs_by_roi: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


class BountyIntelligence:
    """Analyzes aggregated bug bounty program data for intelligence insights."""

    def __init__(self):
        LOG.debug("BountyIntelligence initialized")

    def generate_report(self) -> BountyIntelReport:
        """Generate a comprehensive bug bounty intelligence report."""
        now = datetime.now(timezone.utc).isoformat()
        report = BountyIntelReport(generated_at=now)

        session = SessionLocal()
        try:
            programs = session.query(TargetIntel).all()
        finally:
            session.close()
        if not programs:
            LOG.info("No programs loaded for bounty intelligence report")
            return report

        platforms: dict[str, list[TargetIntel]] = defaultdict(list)
        for p in programs:
            platforms[p.source or "unknown"].append(p)

        total_active = 0
        for platform_name, platform_programs in platforms.items():
            active = [p for p in platform_programs if getattr(p, "is_active", True)]
            total_active += len(active)
            qualities = [p.quality_score or 0 for p in platform_programs]
            rois = [p.roi_score or 0 for p in platform_programs]

            tech_tags: dict[str, int] = defaultdict(int)
            for p in platform_programs:
                raw_tags = (p.technology_tags or "").split(",") if p.technology_tags else []
                for tag in raw_tags:
                    tag = tag.strip()
                    if tag:
                        tech_tags[tag] += 1

            sorted_tech = sorted(tech_tags.items(), key=lambda x: x[1], reverse=True)

            report.platform_metrics[platform_name] = ProgramMetrics(
                platform=platform_name,
                total_programs=len(platform_programs),
                active_programs=len(active),
                avg_quality=round(sum(qualities) / len(qualities), 2) if qualities else 0.0,
                avg_roi=round(sum(rois) / len(rois), 2) if rois else 0.0,
                technology_breakdown=dict(sorted_tech[:15]),
                top_technologies=[t for t, _ in sorted_tech[:5]],
            )

        report.total_programs = len(programs)
        report.total_active = total_active

        sorted_by_quality = sorted(
            programs, key=lambda p: p.quality_score or 0, reverse=True
        )[:10]
        report.top_programs_by_quality = [
            {
                "name": p.name,
                "platform": p.source or "unknown",
                "quality": p.quality_score or 0,
                "roi": p.roi_score or 0,
                "technologies": (p.technology_tags or "").split(",") if p.technology_tags else [],
            }
            for p in sorted_by_quality
        ]

        sorted_by_roi = sorted(
            programs, key=lambda p: p.roi_score or 0, reverse=True
        )[:10]
        report.top_programs_by_roi = [
            {
                "name": p.name,
                "platform": p.source or "unknown",
                "roi": p.roi_score or 0,
                "quality": p.quality_score or 0,
                "technologies": (p.technology_tags or "").split(",") if p.technology_tags else [],
            }
            for p in sorted_by_roi
        ]

        report.summary = self._generate_summary(report)
        return report

    @staticmethod
    def _generate_summary(report: BountyIntelReport) -> str:
        """Generate a plain-language summary of bounty intelligence."""
        parts = []
        parts.append(f"Total programs tracked: {report.total_programs}")
        parts.append(f"Active programs: {report.total_active}")

        if report.platform_metrics:
            top_platform = max(
                report.platform_metrics.values(),
                key=lambda m: m.total_programs,
            )
            parts.append(
                f"Largest platform: {top_platform.platform} "
                f"({top_platform.total_programs} programs)"
            )

            high_quality = [
                m for m in report.platform_metrics.values()
                if m.avg_quality >= 50
            ]
            if high_quality:
                parts.append(
                    "High-quality platforms: "
                    + ", ".join(m.platform for m in high_quality)
                )

        if report.top_programs_by_quality:
            top = report.top_programs_by_quality[0]
            parts.append(f"Top program: {top['name']} (quality: {top['quality']})")

        if report.top_programs_by_roi:
            top_roi = report.top_programs_by_roi[0]
            parts.append(f"Best ROI: {top_roi['name']} (ROI: {top_roi['roi']})")

        return " | ".join(parts) if parts else "No intelligence data available"
