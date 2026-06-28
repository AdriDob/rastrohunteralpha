import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from core_engines.reporting.severity import risk_to_severity
from core_engines.validation.gate import Verdict
from database import models

LOG = logging.getLogger("rastro.validation.verdict_handler")


class VerdictHandler:
    def __init__(self, session: Session):
        self._session = session

    def process_verdict(
        self,
        verdict: Verdict,
        endpoint_id: int,
        target_id: int,
        evidence_records: list[dict[str, Any]],
        comparison_summary: dict[str, Any] | None = None,
    ) -> models.Finding | None:
        db_verdict = self._save_verdict(verdict, endpoint_id, comparison_summary)
        self._save_evidence(db_verdict.id, evidence_records)

        if verdict.status == "confirmed":
            return self._create_finding(verdict, endpoint_id, target_id)
        return None

    def _save_verdict(
        self,
        verdict: Verdict,
        endpoint_id: int,
        comparison_summary: dict[str, Any] | None = None,
    ) -> models.Verdict:
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
                "comparison_summary": comparison_summary or {},
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
        self._session.add(db_verdict)
        self._session.commit()
        self._session.refresh(db_verdict)
        return db_verdict

    def _save_evidence(
        self, verdict_id: int, evidence_records: list[dict[str, Any]]
    ) -> None:
        for rec in evidence_records:
            db_ev = models.Evidence(
                verdict_id=verdict_id,
                endpoint_id=None,
                attempt_label=rec.get("attempt_label", "unknown"),
                request_url=rec.get("request_url", ""),
                request_method=rec.get("request_method", "GET"),
                request_headers=rec.get("request_headers"),
                request_params=rec.get("request_params"),
                request_body=rec.get("request_body"),
                auth_label=rec.get("auth_label", "unknown"),
                response_status=rec.get("response_status", 0),
                response_headers=rec.get("response_headers"),
                response_body=rec.get("response_body"),
                response_body_hash=rec.get("response_body_hash"),
                status_match=rec.get("status_match", "unknown"),
                body_diff_ratio=rec.get("body_diff_ratio", "0.0"),
                sensitive_fields=rec.get("sensitive_fields"),
                consistent=rec.get("consistent", "true"),
                curl_command=rec.get("curl_command"),
            )
            self._session.add(db_ev)

            db_vr = models.ValidationResult(
                verdict_id=verdict_id,
                attempt=int(rec.get("attempt_label", "attempt_1").split("_")[-1]),
                baseline_response=json.dumps({}),
                probe_response=json.dumps({}),
                comparison_summary=json.dumps({
                    "body_diff_ratio": rec.get("body_diff_ratio"),
                    "sensitive_fields": rec.get("sensitive_fields"),
                    "consistent": rec.get("consistent"),
                }),
                has_rate_limit="false",
                has_timeout="false",
                rule_results=json.dumps({}),
            )
            self._session.add(db_vr)

        self._session.commit()

    def _create_finding(
        self, verdict: Verdict, endpoint_id: int, target_id: int
    ) -> models.Finding:
        severity = risk_to_severity(verdict.confidence * 100)

        passed = ", ".join(verdict.validation.passed_rules) if verdict.validation.passed_rules else "none"
        description = (
            f"Validation confirmed ({verdict.confidence:.0%} confidence, "
            f"{verdict.reproducibility_score:.0%} reproducibility). "
            f"Rules passed: {passed}. "
            f"Reason: {verdict.reason}"
        )

        if verdict.validation.passed_rules:
            if "privilege_boundary_break" in verdict.validation.passed_rules:
                title = f"IDOR / Privilege Boundary Break at endpoint {endpoint_id}"
            elif "auth_bypass" in verdict.validation.passed_rules:
                title = f"Authentication Bypass at endpoint {endpoint_id}"
            elif "sensitive_data_exposure" in verdict.validation.passed_rules:
                title = f"Sensitive Data Exposure at endpoint {endpoint_id}"
            elif "cross_session_mismatch" in verdict.validation.passed_rules:
                title = f"Cross-Session Data Mismatch at endpoint {endpoint_id}"
            else:
                title = f"Security Finding at endpoint {endpoint_id}"
        else:
            title = f"Security Finding at endpoint {endpoint_id}"

        finding = models.Finding(
            target_id=target_id,
            endpoint_id=endpoint_id,
            title=title,
            severity=severity,
            description=description,
        )
        self._session.add(finding)
        self._session.commit()
        self._session.refresh(finding)
        return finding
