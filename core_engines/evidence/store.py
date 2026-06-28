import json
import logging
from typing import Any

from core_engines.validation.gate import Verdict
from core_engines.validation.replayer import ComparisonResult
from database import models
from database.db import SessionLocal

LOG = logging.getLogger("rastro.evidence.store")


class EvidenceStore:
    def save_verdict(self, verdict: Verdict, endpoint_id: int | None = None) -> int:
        session = SessionLocal()
        try:
            db_verdict = models.Verdict(
                hot_path_id=verdict.hot_path_id,
                endpoint_id=endpoint_id,
                status=verdict.status,
                confidence=json.dumps({"score": verdict.confidence}),
                reproducibility_score=str(verdict.reproducibility_score),
                validation_report=json.dumps({
                    "passed": verdict.validation.passed,
                    "passed_rules": verdict.validation.passed_rules,
                    "failed_rules": verdict.validation.failed_rules,
                }),
                confidence_details=json.dumps({
                    "score": verdict.confidence_details.score,
                    "breakdown": verdict.confidence_details.breakdown,
                    "level": verdict.confidence_details.level,
                }),
                evidence_links=json.dumps(verdict.evidence_links),
                reason=verdict.reason,
                retry_count=verdict.retry_count,
            )
            session.add(db_verdict)
            session.commit()
            session.refresh(db_verdict)
            return db_verdict.id
        except Exception as exc:
            LOG.error("Failed to save verdict: %s", exc)
            session.rollback()
            raise
        finally:
            session.close()

    def save_comparison(
        self,
        verdict_id: int,
        attempt: int,
        result: ComparisonResult,
        auth_label: str,
        endpoint_id: int | None = None,
    ) -> int:
        session = SessionLocal()
        try:
            db_ev = models.Evidence(
                verdict_id=verdict_id,
                endpoint_id=endpoint_id,
                attempt_label=f"attempt_{attempt}",
                request_url="",
                request_method=result.baseline.headers.get("__method", "GET") or "GET",
                request_headers=json.dumps(result.baseline.headers) if result.baseline.headers else None,
                auth_label=auth_label,
                response_status=result.probe.status_code,
                response_headers=json.dumps(result.probe.headers),
                response_body=result.probe.body[:5000],
                response_body_hash=result.probe.body_hash,
                status_match=str(result.status_match),
                body_diff_ratio=str(result.body_diff_ratio),
                sensitive_fields=json.dumps(result.sensitive_fields_detected),
                consistent=str(result.consistent),
            )
            session.add(db_ev)
            session.commit()
            session.refresh(db_ev)

            db_vr = models.ValidationResult(
                verdict_id=verdict_id,
                attempt=attempt,
                baseline_response=json.dumps({
                    "status": result.baseline.status_code,
                    "body_hash": result.baseline.body_hash,
                    "elapsed_ms": result.baseline.elapsed_ms,
                }),
                probe_response=json.dumps({
                    "status": result.probe.status_code,
                    "body_hash": result.probe.body_hash,
                    "elapsed_ms": result.probe.elapsed_ms,
                }),
                comparison_summary=json.dumps({
                    "status_match": result.status_match,
                    "body_diff_ratio": result.body_diff_ratio,
                    "headers_diff": {k: list(v) for k, v in result.headers_diff.items()},
                    "sensitive_fields": result.sensitive_fields_detected,
                }),
                has_rate_limit=str(result.has_rate_limit),
                has_timeout=str(result.has_timeout),
            )
            session.add(db_vr)
            session.commit()
            return db_ev.id
        except Exception as exc:
            LOG.error("Failed to save comparison: %s", exc)
            session.rollback()
            raise
        finally:
            session.close()

    def get_verdicts_by_status(self, status: str) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            rows = (
                session.query(models.Verdict)
                .filter(models.Verdict.status == status)
                .order_by(models.Verdict.created_at.desc())
                .all()
            )
            return [
                {
                    "id": v.id,
                    "hot_path_id": v.hot_path_id,
                    "status": v.status,
                    "confidence": json.loads(v.confidence) if v.confidence else {},
                    "reason": v.reason,
                    "retry_count": v.retry_count,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in rows
            ]
        finally:
            session.close()

    def get_evidence_for_verdict(self, verdict_id: int) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            rows = (
                session.query(models.Evidence)
                .filter(models.Evidence.verdict_id == verdict_id)
                .all()
            )
            return [
                {
                    "id": e.id,
                    "attempt": e.attempt_label,
                    "response_status": e.response_status,
                    "body_diff_ratio": e.body_diff_ratio,
                    "sensitive_fields": json.loads(e.sensitive_fields) if e.sensitive_fields else [],
                    "consistent": e.consistent,
                    "curl_command": e.curl_command,
                }
                for e in rows
            ]
        finally:
            session.close()

    def batch_get_evidence_for_verdicts(self, verdict_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
        if not verdict_ids:
            return {}
        session = SessionLocal()
        try:
            rows = (
                session.query(models.Evidence)
                .filter(models.Evidence.verdict_id.in_(verdict_ids))
                .all()
            )
            result: dict[int, list[dict[str, Any]]] = {vid: [] for vid in verdict_ids}
            for e in rows:
                result.setdefault(e.verdict_id, []).append({
                    "id": e.id,
                    "attempt": e.attempt_label,
                    "response_status": e.response_status,
                    "body_diff_ratio": e.body_diff_ratio,
                    "sensitive_fields": json.loads(e.sensitive_fields) if e.sensitive_fields else [],
                    "consistent": e.consistent,
                    "curl_command": e.curl_command,
                })
            return result
        finally:
            session.close()
