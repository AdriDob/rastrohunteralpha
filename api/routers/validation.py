from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/validation", tags=["validation"])


class AuthContextModel(BaseModel):
    token: Optional[str] = None
    label: str = "baseline"


class ValidateHotPathRequest(BaseModel):
    hot_path_id: str
    endpoint_id: int
    target_id: int
    url: str
    method: str = "GET"
    headers: Optional[dict[str, str]] = None
    params: Optional[dict[str, Any]] = None
    body: Optional[str] = None
    auth_baseline_token: Optional[str] = None
    auth_baseline_label: str = "baseline"
    auth_probe_token: Optional[str] = None
    auth_probe_label: str = "probe"
    mutations: Optional[dict[str, Any]] = None
    min_attempts: int = 3


@router.post("/validate")
def validate_and_report(request: ValidateHotPathRequest):
    from database import db, models
    from core.validation.loop_engine import ValidationLoopEngine
    from core.validation.replayer import AuthContext, RequestSpec
    from core.validation.verdict_handler import VerdictHandler
    from core.validation.evidence_builder import EvidenceBuilder
    from core.reporting.reporting import ReportGenerator

    import logging
    logger = logging.getLogger("rastro.api.validation")

    session = db.SessionLocal()
    try:
        endpoint = (
            session.query(models.Endpoint)
            .filter(models.Endpoint.id == request.endpoint_id)
            .first()
        )
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        validation_engine = ValidationLoopEngine()
        request_spec = RequestSpec(
            url=request.url,
            method=request.method,
            headers=request.headers or {},
            params=request.params or {},
            body=request.body,
        )

        auth_baseline = AuthContext(
            token=request.auth_baseline_token,
            label=request.auth_baseline_label,
        )
        auth_probe = AuthContext(
            token=request.auth_probe_token,
            label=request.auth_probe_label,
        )

        logger.info(
            f"Running validation loop: {request.method} {request.url} "
            f"with {request.min_attempts} attempts"
        )

        verdict = validation_engine.evaluate(
            hot_path_id=request.hot_path_id,
            endpoint_details={
                "url": request.url,
                "method": request.method,
                "headers": request.headers or {},
                "params": request.params or {},
                "body": request.body,
            },
            endpoint_signals=endpoint.parsed_params,
            auth_baseline=auth_baseline,
            auth_probe=auth_probe,
            mutations=request.mutations or {},
            min_attempts=request.min_attempts,
        )

        verdict_handler = VerdictHandler(session=session)
        saved_verdict = verdict_handler.new(verdict)
        verdict_id = saved_verdict.get("id") or saved_verdict.get("verdict_id")

        evidence_builder = EvidenceBuilder(
            hot_path_id=request.hot_path_id,
            verdict_id=verdict_id,
        )
        evidence_builder.capture(
            request_spec=request_spec,
            auth_baseline=auth_baseline,
            auth_probe=auth_probe,
            min_attempts=request.min_attempts,
        )
        evidence_data = evidence_builder.build(session=session)

        response = {
            "verdict": saved_verdict,
            "evidence": evidence_data,
            "validated": True,
        }

        if verdict.get("status") == "confirmed" and float(verdict.get("confidence", 0)) >= 0.6:
            try:
                reporting = ReportGenerator(session=session)
                report_result = reporting.generate(
                    hot_path_id=request.hot_path_id,
                    endpoint_id=request.endpoint_id,
                    findings={
                        "verdict": saved_verdict,
                        "evidence": evidence_data,
                    },
                )
                response["report"] = report_result
            except Exception as e:
                logger.warning(f"Report generation failed: {e}")
                response["report_error"] = str(e)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
    finally:
        session.close()
