from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/validation", tags=["idor"])


class IDORScanRequest(BaseModel):
    target_id: int
    endpoint_id: int
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    identity_baseline_id: int
    identity_probe_id: Optional[int] = None


class IDORResultItem(BaseModel):
    parameter: str
    original_value: str
    probe_value: str
    baseline_status: int
    probe_status: int
    body_diff_ratio: float
    sensitive_fields_leaked: List[str]
    verdict: str
    reason: str


class IDORScanResponse(BaseModel):
    total_tests: int
    vulnerable: List[IDORResultItem]
    blocked: List[IDORResultItem]
    inconclusive: List[IDORResultItem]
    elapsed_ms: int
    summary: str


@router.post("/idor", response_model=IDORScanResponse)
def idor_scan(request: IDORScanRequest):
    from database import db, models
    from core_engines.target_auth.session_resolver import get_session_resolver
    from core_engines.target_auth.idor_tester import IDORTester
    from core_engines.validation.replayer import AuthContext

    logger = logging.getLogger("rastro.api.idor")
    session = db.SessionLocal()
    try:
        endpoint = (
            session.query(models.Endpoint)
            .filter(models.Endpoint.id == request.endpoint_id)
            .first()
        )
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        resolver = get_session_resolver()
        baseline_ctx = resolver.resolve(request.identity_baseline_id)
        if not baseline_ctx:
            raise HTTPException(
                status_code=400,
                detail=f"Baseline identity {request.identity_baseline_id} has no valid session",
            )

        probe_ctx = None
        if request.identity_probe_id:
            probe_ctx = resolver.resolve(request.identity_probe_id)
        if not probe_ctx:
            probe_ctx = {"token": None, "cookies": {}, "headers": {}}

        baseline_auth = AuthContext(
            token=baseline_ctx.get("token"),
            cookies=baseline_ctx.get("cookies", {}),
            headers=baseline_ctx.get("headers", {}),
            label=baseline_ctx.get("label", "baseline"),
        )
        probe_auth = AuthContext(
            token=probe_ctx.get("token"),
            cookies=probe_ctx.get("cookies", {}),
            headers=probe_ctx.get("headers", {}),
            label=probe_ctx.get("label", "probe"),
        )

        tester = IDORTester()
        report = tester.scan(
            target_id=request.target_id,
            endpoint_id=request.endpoint_id,
            baseline_auth=baseline_auth,
            probe_auth=probe_auth,
            url=request.url,
            method=request.method,
            headers=request.headers,
            params=request.params,
            body=request.body,
        )

        vulnerable_count = len(report.vulnerable)
        blocked_count = len(report.blocked)
        inconclusive_count = len(report.inconclusive)

        if vulnerable_count > 0:
            summary = f"Found {vulnerable_count} potential IDOR vulnerabilities out of {report.total_tests} tests"
        elif blocked_count > 0:
            summary = f"No IDOR found — {blocked_count} tests blocked (access denied)"
        else:
            summary = f"No IDOR detected — {inconclusive_count} inconclusive, {report.total_tests} total tests"

        return IDORScanResponse(
            total_tests=report.total_tests,
            vulnerable=[
                IDORResultItem(
                    parameter=r.parameter,
                    original_value=r.original_value,
                    probe_value=r.probe_value,
                    baseline_status=r.baseline_status,
                    probe_status=r.probe_status,
                    body_diff_ratio=r.body_diff_ratio,
                    sensitive_fields_leaked=r.sensitive_fields_leaked,
                    verdict=r.verdict,
                    reason=r.reason,
                )
                for r in report.vulnerable
            ],
            blocked=[
                IDORResultItem(
                    parameter=r.parameter,
                    original_value=r.original_value,
                    probe_value=r.probe_value,
                    baseline_status=r.baseline_status,
                    probe_status=r.probe_status,
                    body_diff_ratio=r.body_diff_ratio,
                    sensitive_fields_leaked=r.sensitive_fields_leaked,
                    verdict=r.verdict,
                    reason=r.reason,
                )
                for r in report.blocked
            ],
            inconclusive=[
                IDORResultItem(
                    parameter=r.parameter,
                    original_value=r.original_value,
                    probe_value=r.probe_value,
                    baseline_status=r.baseline_status,
                    probe_status=r.probe_status,
                    body_diff_ratio=r.body_diff_ratio,
                    sensitive_fields_leaked=r.sensitive_fields_leaked,
                    verdict=r.verdict,
                    reason=r.reason,
                )
                for r in report.inconclusive
            ],
            elapsed_ms=report.elapsed_ms,
            summary=summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IDOR scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"IDOR scan failed: {str(e)}")
    finally:
        session.close()
