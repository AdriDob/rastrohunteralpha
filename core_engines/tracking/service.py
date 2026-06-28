from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from core_engines.platforms import get_platform
from core_engines.settings.service import get_platform_config

logger = logging.getLogger("rastro.tracking")

PLATFORM_STATE_MAP: dict[str, str] = {
    "new": "submitted",
    "triaged": "triaged",
    "resolved": "resolved",
    "paid": "paid",
    "closed": "closed",
    "duplicate": "duplicate",
    "informative": "informative",
    "not_applicable": "na",
    "needs_more_info": "need_more_info",
}


def _get_session():
    from database.db import SessionLocal
    return SessionLocal()


def _save_submission_record(
    report_id: int,
    platform: str,
    external_id: str,
    status: str = "submitted",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from database.models import SubmissionRecord
    session = _get_session()
    try:
        existing = (
            session.query(SubmissionRecord)
            .filter(
                SubmissionRecord.report_id == report_id,
                SubmissionRecord.platform == platform,
            )
            .first()
        )
        if existing:
            existing.external_id = external_id or existing.external_id
            existing.status = status
            existing.last_update = datetime.now(timezone.utc)
            if extra:
                existing.extra_data = json.dumps(extra, ensure_ascii=False)
        else:
            record = SubmissionRecord(
                report_id=report_id,
                platform=platform,
                external_id=external_id,
                status=status,
                extra_data=json.dumps(extra or {}, ensure_ascii=False),
            )
            session.add(record)
        session.commit()
        return {
            "report_id": report_id,
            "platform": platform,
            "external_id": external_id,
            "status": status,
        }
    except Exception as exc:
        session.rollback()
        logger.error("Failed to save submission record: %s", exc)
        return {"report_id": report_id, "platform": platform, "status": "error", "error": str(exc)}
    finally:
        session.close()


def submit_report_to_platform(
    report_id: int,
    platform: str,
) -> dict[str, Any]:
    from core_engines.pipeline.report_service import get_report

    session = _get_session()
    try:
        report = get_report(session, report_id)
    finally:
        session.close()

    if not report:
        return {"success": False, "error": f"Report {report_id} not found"}

    platform_cls = get_platform(platform)
    if not platform_cls:
        return {"success": False, "error": f"Unknown platform: {platform}"}

    config = get_platform_config(platform)
    if not config.get("enabled"):
        return {"success": False, "error": f"Platform {platform} is not enabled"}

    api_key = config.get("api_key", "")
    if not api_key:
        return {"success": False, "error": f"No API key configured for {platform}"}

    result = platform_cls.submit(report, api_key)
    if result.success:
        _save_submission_record(
            report_id=report_id,
            platform=platform,
            external_id=result.external_id,
            status="submitted",
            extra={"url": result.url, "data": result.data},
        )
        return {
            "success": True,
            "external_id": result.external_id,
            "url": result.url,
        }
    return {"success": False, "error": result.error}


def handle_webhook_callback(
    platform: str,
    external_id: str,
    status: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from database.models import SubmissionRecord
    session = _get_session()
    try:
        record = (
            session.query(SubmissionRecord)
            .filter(
                SubmissionRecord.platform == platform,
                SubmissionRecord.external_id == external_id,
            )
            .first()
        )
        if not record:
            return {"error": f"No submission found for {platform}/{external_id}"}

        mapped_status = PLATFORM_STATE_MAP.get(status, status)
        record.status = mapped_status
        record.last_update = datetime.now(timezone.utc)
        if extra:
            existing = json.loads(record.extra_data) if record.extra_data else {}
            existing.update(extra)
            record.extra_data = json.dumps(existing, ensure_ascii=False)

        # Also update the report status
        from database.models import Report
        report = session.query(Report).filter(Report.id == record.report_id).first()
        if report:
            report.status = mapped_status
            report.updated_at = datetime.now(timezone.utc)
            # Update confirmed reward if paid
            if mapped_status == "paid" and extra and "reward" in extra:
                report.confirmed_reward = float(extra["reward"])

        session.commit()
        return {
            "report_id": record.report_id,
            "platform": platform,
            "external_id": external_id,
            "status": mapped_status,
        }
    except Exception as exc:
        session.rollback()
        logger.error("Webhook callback failed: %s", exc)
        return {"error": str(exc)}
    finally:
        session.close()


def get_submission_status(report_id: int) -> list[dict[str, Any]]:
    from database.models import SubmissionRecord
    session = _get_session()
    try:
        records = (
            session.query(SubmissionRecord)
            .filter(SubmissionRecord.report_id == report_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "platform": r.platform,
                "external_id": r.external_id,
                "status": r.status,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else "",
                "last_update": r.last_update.isoformat() if r.last_update else "",
            }
            for r in records
        ]
    finally:
        session.close()
