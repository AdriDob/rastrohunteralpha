import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from database.db import SessionLocal

LOG = logging.getLogger("rastro.replay")


@dataclass(frozen=True)
class ReplayFrame:
    stage: str
    timestamp: str
    data: dict[str, Any]
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Replay:
    target_id: int
    target_name: str
    domain: str | None
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    timeline: list[ReplayFrame] = field(default_factory=list)
    endpoints: list[dict[str, Any]] = field(default_factory=list)
    hot_paths: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    verdicts: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    reports: list[dict[str, Any]] = field(default_factory=list)
    screenshots: list[dict[str, Any]] = field(default_factory=list)
    quick_wins: list[dict[str, Any]] = field(default_factory=list)
    ai_explanations: list[dict[str, Any]] = field(default_factory=list)
    memory_records: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "domain": self.domain,
            "generated_at": self.generated_at,
            "timeline": [f.to_dict() for f in sorted(self.timeline, key=lambda x: x.timestamp)],
            "endpoints": self.endpoints,
            "hot_paths": self.hot_paths,
            "evidence": self.evidence,
            "verdicts": self.verdicts,
            "findings": self.findings,
            "reports": self.reports,
            "screenshots": self.screenshots,
            "quick_wins": self.quick_wins,
            "ai_explanations": self.ai_explanations,
            "memory_records": self.memory_records,
            "total_frames": len(self.timeline),
        }


def build_replay(target_id: int) -> Replay:
    session = SessionLocal()
    try:
        from database.models import (
            Endpoint,
            Evidence,
            Finding,
            MemoryRecord,
            ScanRun,
            Target,
            Verdict,
        )

        t = session.query(Target).filter(Target.id == target_id).first()
        if t is None:
            raise ValueError(f"Target {target_id} not found")

        replay = Replay(
            target_id=t.id,
            target_name=t.name,
            domain=t.domain,
        )

        # Endpoints
        endpoints = (
            session.query(Endpoint)
            .filter(Endpoint.target_id == target_id)
            .order_by(Endpoint.discovered_at)
            .all()
        )
        for ep in endpoints:
            ep_dict = {
                "id": ep.id,
                "path": ep.path,
                "method": ep.method,
                "discovered_at": ep.discovered_at.isoformat() if ep.discovered_at else None,
            }
            if ep.params:
                try:
                    ep_dict["params"] = json.loads(ep.params) if isinstance(ep.params, str) else ep.params
                except (json.JSONDecodeError, ValueError):
                    ep_dict["params"] = {}
            replay.endpoints.append(ep_dict)
            replay.timeline.append(ReplayFrame(
                stage="endpoint_discovered",
                timestamp=ep.discovered_at.isoformat() if ep.discovered_at else "",
                data={"endpoint_id": ep.id, "path": ep.path, "method": ep.method},
                summary=f"Endpoint: {ep.method} {ep.path}",
            ))

        # Findings
        findings = (
            session.query(Finding)
            .filter(Finding.target_id == target_id)
            .order_by(Finding.created_at)
            .all()
        )
        for f in findings:
            replay.findings.append({
                "id": f.id,
                "title": f.title,
                "severity": f.severity,
                "description": f.description,
                "endpoint_id": f.endpoint_id,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            })
            replay.timeline.append(ReplayFrame(
                stage="finding_created",
                timestamp=f.created_at.isoformat() if f.created_at else "",
                data={"finding_id": f.id, "title": f.title, "severity": f.severity},
                summary=f"Finding: {f.title} ({f.severity})",
            ))

        # Verdicts and evidence
        verdicts = (
            session.query(Verdict)
            .filter(
                Verdict.endpoint_id.in_(
                    session.query(Endpoint.id).filter(Endpoint.target_id == target_id).subquery()
                )
            )
            .order_by(Verdict.created_at)
            .all()
        ) if endpoints else []

        for v in verdicts:
            v_dict = {
                "id": v.id,
                "hot_path_id": v.hot_path_id,
                "status": v.status,
                "confidence": float(v.confidence) if v.confidence else None,
                "reason": v.reason,
                "retry_count": v.retry_count,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            replay.verdicts.append(v_dict)
            replay.timeline.append(ReplayFrame(
                stage="verdict_assigned",
                timestamp=v.created_at.isoformat() if v.created_at else "",
                data={"verdict_id": v.id, "status": v.status, "confidence": v_dict["confidence"]},
                summary=f"Verdict: {v.status} (confidence: {v_dict['confidence']})",
            ))

            # Evidence for this verdict
            ev_list = (
                session.query(Evidence)
                .filter(Evidence.verdict_id == v.id)
                .order_by(Evidence.created_at)
                .all()
            )
            for ev in ev_list:
                replay.evidence.append({
                    "id": ev.id,
                    "attempt_label": ev.attempt_label,
                    "request_url": ev.request_url,
                    "request_method": ev.request_method,
                    "response_status": ev.response_status,
                    "consistent": ev.consistent,
                    "body_diff_ratio": ev.body_diff_ratio,
                    "curl_command": ev.curl_command,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                })
                replay.timeline.append(ReplayFrame(
                    stage="evidence_generated",
                    timestamp=ev.created_at.isoformat() if ev.created_at else "",
                    data={"evidence_id": ev.id, "verdict_id": v.id, "status": ev.response_status},
                    summary=f"Evidence: attempt {ev.attempt_label} ({ev.response_status})",
                ))

        # Hot paths from endpoint params
        for ep in endpoints:
            try:
                params = json.loads(ep.params) if isinstance(ep.params, str) else (ep.params or {})
            except (json.JSONDecodeError, ValueError):
                params = {}
            if isinstance(params, dict) and params.get("hot_path"):
                replay.hot_paths.append({
                    "endpoint_id": ep.id,
                    "path": ep.path,
                    "method": ep.method,
                    "data": params["hot_path"],
                })

        # Scans
        scans = (
            session.query(ScanRun)
            .filter(ScanRun.target_id == target_id)
            .order_by(ScanRun.started_at)
            .all()
        )
        for scan in scans:
            replay.timeline.append(ReplayFrame(
                stage="recon",
                timestamp=scan.started_at.isoformat() if scan.started_at else "",
                data={
                    "scan_id": scan.id,
                    "mode": scan.mode,
                    "status": scan.status,
                    "endpoint_count": scan.endpoint_count,
                },
                summary=f"Scan: {scan.mode} ({scan.status}, {scan.endpoint_count} endpoints)",
            ))

        # Memory records
        memories = (
            session.query(MemoryRecord)
            .filter(
                MemoryRecord.category.in_(["learning_snapshot", "pattern", "timeline"])
            )
            .order_by(MemoryRecord.created_at.desc())
            .limit(20)
            .all()
        )
        for mr in memories:
            replay.memory_records.append({
                "id": mr.id,
                "category": mr.category,
                "key": mr.key,
                "created_at": mr.created_at.isoformat() if mr.created_at else None,
            })

        return replay

    finally:
        session.close()


def list_replay_targets() -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        from database.models import Target
        targets = session.query(Target).order_by(Target.created_at.desc()).limit(50).all()
        return [
            {"id": t.id, "name": t.name, "domain": t.domain, "created_at": t.created_at.isoformat() if t.created_at else None}
            for t in targets
        ]
    finally:
        session.close()
