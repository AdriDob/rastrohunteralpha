from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/validation", tags=["validation"])


class AuthContextModel(BaseModel):
    token: str | None = None
    label: str = "baseline"


class ValidateHotPathRequest(BaseModel):
    hot_path_id: str
    endpoint_id: int
    target_id: int
    url: str
    method: str = "GET"
    headers: dict[str, str] | None = None
    params: dict[str, Any] | None = None
    body: str | None = None
    # Legacy: raw token strings
    auth_baseline_token: str | None = None
    auth_baseline_label: str = "baseline"
    auth_probe_token: str | None = None
    auth_probe_label: str = "probe"
    # Phase 2: identity-based auth (preferred)
    identity_baseline_id: int | None = None
    identity_probe_id: int | None = None
    mutations: dict[str, Any] | None = None
    min_attempts: int = 3


def _resolve_auth(
    identity_id: int | None,
    raw_token: str | None,
    fallback_label: str,
) -> dict | None:
    """Resolve auth context from identity_id or raw token.

    Returns AuthContext-compatible dict or None.
    """
    if identity_id is not None:
        from core_engines.target_auth.session_resolver import get_session_resolver
        ctx = get_session_resolver().resolve(identity_id)
        if ctx:
            ctx["label"] = fallback_label
            return ctx
    if raw_token:
        return {"token": raw_token, "cookies": {}, "headers": {}, "label": fallback_label}
    return None


@router.post("/validate")
def validate_and_report(request: ValidateHotPathRequest):
    import logging

    from core_engines.pipeline.report_service import generate_and_save_report
    from core_engines.validation.evidence_builder import EvidenceBuilder
    from core_engines.validation.loop_engine import ValidationLoopEngine
    from core_engines.validation.replayer import AuthContext, RequestSpec
    from core_engines.validation.verdict_handler import VerdictHandler
    from database import db, models
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
        RequestSpec(
            url=request.url,
            method=request.method,
            headers=request.headers or {},
            params=request.params or {},
            body=request.body,
        )

        baseline = _resolve_auth(
            request.identity_baseline_id,
            request.auth_baseline_token,
            request.auth_baseline_label,
        )
        probe = _resolve_auth(
            request.identity_probe_id,
            request.auth_probe_token,
            request.auth_probe_label,
        )

        if baseline is None and probe is None:
            raise HTTPException(
                status_code=400,
                detail="At least one auth context required: provide identity_baseline_id, auth_baseline_token, or both",
            )

        auth_baseline = AuthContext(
            token=baseline.get("token") if baseline else None,
            cookies=baseline.get("cookies", {}) if baseline else {},
            headers=baseline.get("headers", {}) if baseline else {},
            label=(baseline or {}).get("label", "anonymous"),
        )
        auth_probe = AuthContext(
            token=probe.get("token") if probe else None,
            cookies=probe.get("cookies", {}) if probe else {},
            headers=probe.get("headers", {}) if probe else {},
            label=(probe or {}).get("label", "anonymous"),
        )

        logger.info(
            f"Running validation loop: {request.method} {request.url} "
            f"with {request.min_attempts} attempts "
            f"(baseline={auth_baseline.label}, probe={auth_probe.label})"
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

        evidence_builder = EvidenceBuilder()
        comparison_summary = evidence_builder.build_comparison_summary([])

        handler = VerdictHandler(session=session)
        finding = handler.process_verdict(
            verdict=verdict,
            endpoint_id=request.endpoint_id,
            target_id=request.target_id,
            evidence_records=[],
            comparison_summary=comparison_summary,
        )

        db_verdict = (
            session.query(models.Verdict)
            .filter(models.Verdict.hot_path_id == verdict.hot_path_id)
            .order_by(models.Verdict.id.desc())
            .first()
        )
        verdict_id = db_verdict.id if db_verdict else None

        response = {
            "verdict": {
                "id": verdict_id,
                "status": verdict.status,
                "confidence": verdict.confidence,
                "reason": verdict.reason,
            },
            "evidence": [],
            "validated": True,
        }

        report_id = None
        if verdict.status == "confirmed" and verdict.confidence >= 0.6:
            from core_engines.pipeline.stages import PipelineContext
            ctx = PipelineContext(
                hot_path_id=request.hot_path_id,
                endpoint_id=request.endpoint_id,
                target_id=request.target_id,
            )
            ctx.finding_id = finding.id if finding else None
            try:
                ctx = generate_and_save_report(
                    session=session,
                    ctx=ctx,
                    verdict=verdict,
                    endpoint=endpoint,
                    findings_data={
                        "verdict": verdict.status,
                        "confidence": verdict.confidence,
                    },
                )
                report_id = ctx.report_id
                response["report_id"] = report_id
            except Exception as e:
                logger.warning(f"Report generation failed: {e}")
                response["report_error"] = str(e)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}") from e
    finally:
        session.close()


class BatchValidateRequest(BaseModel):
    target_id: int
    identity_baseline_id: int
    identity_probe_id: int | None = None
    limit: int = 10
    min_risk_score: float = 25.0


@router.post("/batch")
def batch_validate(request: BatchValidateRequest):
    """Validate all actionable endpoints for a target in batch.

    Uses the identity-based auth (Phase 2). Falls back to anonymous for probe.
    Only processes endpoints with risk_score >= min_risk_score.
    """
    import logging

    from core_engines.engine.unified_scoring import score as unified_score
    from core_engines.target_auth.session_resolver import get_session_resolver
    from core_engines.validation.loop_engine import ValidationLoopEngine
    from core_engines.validation.replayer import AuthContext
    from core_engines.validation.verdict_handler import VerdictHandler
    from database import db, models
    logger = logging.getLogger("rastro.api.validation.batch")
    session_db = db.SessionLocal()

    try:
        # Resolve baseline auth once
        resolver = get_session_resolver()
        baseline_ctx = resolver.resolve(request.identity_baseline_id)
        if not baseline_ctx:
            raise HTTPException(status_code=400, detail="Baseline identity has no valid session")

        probe_ctx = resolver.resolve(request.identity_probe_id) if request.identity_probe_id else None

        auth_baseline = AuthContext(
            token=baseline_ctx.get("token"),
            cookies=baseline_ctx.get("cookies", {}),
            headers=baseline_ctx.get("headers", {}),
            label=baseline_ctx.get("label", "baseline"),
        )
        auth_probe = AuthContext(
            token=probe_ctx.get("token") if probe_ctx else None,
            cookies=probe_ctx.get("cookies", {}) if probe_ctx else {},
            headers=probe_ctx.get("headers", {}) if probe_ctx else {},
            label=(probe_ctx or {}).get("label", "anonymous"),
        )

        # Fetch candidate endpoints
        endpoints = (
            session_db.query(models.Endpoint)
            .filter(models.Endpoint.target_id == request.target_id)
            .limit(request.limit)
            .all()
        )

        engine = ValidationLoopEngine()
        results = []

        for ep in endpoints:
            signals = ep.parsed_params
            score_result = unified_score(ep.path, ep.method, signals.get("params", {}))
            risk_score = score_result.get("risk_score", 0)

            if risk_score < request.min_risk_score:
                continue

            hot_path_id = f"batch-{ep.id}"

            verdict = engine.evaluate(
                hot_path_id=hot_path_id,
                endpoint_details={
                    "url": f"https://{ep.path}" if not ep.path.startswith("http") else ep.path,
                    "method": ep.method,
                    "headers": {},
                    "params": signals.get("params", {}),
                    "body": None,
                },
                endpoint_signals=signals,
                auth_baseline=auth_baseline,
                auth_probe=auth_probe,
                mutations={},
                min_attempts=2,
            )

            verdict_handler = VerdictHandler(session=session_db)
            saved_verdict = verdict_handler.new(verdict)

            results.append({
                "endpoint_id": ep.id,
                "path": ep.path,
                "method": ep.method,
                "risk_score": risk_score,
                "verdict": saved_verdict,
            })

        return {"results": results, "total": len(results)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch validation failed: {str(e)}") from e
    finally:
        session_db.close()
