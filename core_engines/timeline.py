import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from database.db import SessionLocal

LOG = logging.getLogger("rastro.timeline")

EVENT_TYPES = frozenset({
    "recon",
    "endpoint_discovered",
    "graph_updated",
    "hot_path_detected",
    "differential_triggered",
    "evidence_generated",
    "verdict_assigned",
    "report_generated",
    "ai_explanation",
    "quick_win_created",
    "historical_memory_updated",
})


@dataclass(frozen=True)
class TimelineEvent:
    event_type: str
    timestamp: str
    source: str
    description: str
    target_id: int | None = None
    target_name: str | None = None
    endpoint_id: int | None = None
    endpoint_path: str | None = None
    verdict_id: int | None = None
    verdict_status: str | None = None
    finding_id: int | None = None
    report_title: str | None = None
    confidence: float | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __post_init__(self) -> None:
        if self.event_type not in EVENT_TYPES:
            object.__setattr__(self, "event_type", "other")


@dataclass
class Timeline:
    events: list[TimelineEvent] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add(self, event: TimelineEvent) -> None:
        self.events.append(event)

    def sort(self) -> None:
        self.events.sort(key=lambda e: e.timestamp)

    def filter_by_type(self, event_type: str) -> list[TimelineEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def filter_by_target(self, target_id: int) -> list[TimelineEvent]:
        return [e for e in self.events if e.target_id == target_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [e.to_dict() for e in sorted(self.events, key=lambda x: x.timestamp)],
            "total_events": len(self.events),
            "generated_at": self.generated_at,
        }


def build_timeline(
    target_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    event_type: str | None = None,
) -> Timeline:
    session = SessionLocal()
    try:
        from database.models import Endpoint, Evidence, MemoryRecord, ScanRun, Target, Verdict

        timeline = Timeline()

        if target_id:
            targets = session.query(Target).filter(Target.id == target_id).all()
        else:
            targets = session.query(Target).order_by(Target.created_at.desc()).limit(20).all()

        # Add target creation events
        for t in targets:
            timeline.add(TimelineEvent(
                event_type="recon",
                timestamp=t.created_at.isoformat() if t.created_at else "",
                source="system",
                description=f"Target added: {t.name}",
                target_id=t.id,
                target_name=t.name,
            ))

        # Add endpoint discovery events
        for t in targets:
            eps = (
                session.query(Endpoint)
                .filter(Endpoint.target_id == t.id)
                .order_by(Endpoint.discovered_at.desc())
                .limit(50)
                .all()
            )
            for ep in eps:
                timeline.add(TimelineEvent(
                    event_type="endpoint_discovered",
                    timestamp=ep.discovered_at.isoformat() if ep.discovered_at else "",
                    source="recon",
                    description=f"Endpoint discovered: {ep.method} {ep.path}",
                    target_id=t.id,
                    target_name=t.name,
                    endpoint_id=ep.id,
                    endpoint_path=f"{ep.method} {ep.path}",
                ))

        # Add verdict events
        verdict_query = session.query(Verdict)
        if target_id:
            endpoint_ids = [
                e.id for e in session.query(Endpoint.id).filter(Endpoint.target_id == target_id).all()
            ]
            if endpoint_ids:
                verdict_query = verdict_query.filter(Verdict.endpoint_id.in_(endpoint_ids))
        for v in verdict_query.order_by(Verdict.created_at.desc()).limit(limit).all():
            ep = (
                session.query(Endpoint).filter(Endpoint.id == v.endpoint_id).first()
                if v.endpoint_id
                else None
            )
            t = next((t for t in targets if t.id == (ep.target_id if ep else None)), None)
            timeline.add(TimelineEvent(
                event_type="verdict_assigned",
                timestamp=v.created_at.isoformat() if v.created_at else "",
                source="validation",
                description=f"Verdict {v.status}",
                target_id=ep.target_id if ep else None,
                target_name=t.name if t else None,
                endpoint_id=v.endpoint_id,
                verdict_id=v.id,
                verdict_status=v.status,
                confidence=float(v.confidence) if v.confidence else None,
            ))

        # Add evidence events
        ev_query = session.query(Evidence).order_by(Evidence.created_at.desc()).limit(limit)
        for ev in ev_query.all():
            timeline.add(TimelineEvent(
                event_type="evidence_generated",
                timestamp=ev.created_at.isoformat() if ev.created_at else "",
                source="validation",
                description=f"Evidence: {ev.attempt_label} ({ev.response_status})",
                endpoint_id=ev.endpoint_id,
                verdict_id=ev.verdict_id,
                metadata={"response_status": ev.response_status, "consistent": ev.consistent},
            ))

        # Add scan events
        scan_query = session.query(ScanRun)
        if target_id:
            scan_query = scan_query.filter(ScanRun.target_id == target_id)
        for scan in scan_query.order_by(ScanRun.started_at.desc()).limit(20).all():
            t = session.query(Target).filter(Target.id == scan.target_id).first()
            timeline.add(TimelineEvent(
                event_type="recon",
                timestamp=scan.started_at.isoformat() if scan.started_at else "",
                source="scanner",
                description=f"Scan {scan.status}: {scan.mode} mode ({scan.endpoint_count} endpoints)",
                target_id=scan.target_id,
                target_name=t.name if t else None,
                duration_ms=(
                    (scan.finished_at - scan.started_at).total_seconds() * 1000
                    if scan.finished_at and scan.started_at
                    else None
                ),
            ))

        # Add memory/learning events
        mem_records = (
            session.query(MemoryRecord)
            .filter(MemoryRecord.category == "learning_snapshot")
            .order_by(MemoryRecord.created_at.desc())
            .limit(10)
            .all()
        )
        for mr in mem_records:
            timeline.add(TimelineEvent(
                event_type="historical_memory_updated",
                timestamp=mr.created_at.isoformat() if mr.created_at else "",
                source="intelligence",
                description=f"Learning snapshot: {mr.key}",
                metadata={"memory_id": mr.id, "category": mr.category},
            ))

        timeline.sort()

        # Apply filters
        if event_type:
            timeline.events = timeline.filter_by_type(event_type)

        # Apply pagination
        timeline.events = timeline.events[offset:offset + limit]

        return timeline

    finally:
        session.close()
