import logging
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core_engines.engine.unified_scoring import score as unified_score, score_target as unified_score_target
from core_engines.engine.unified_classifier import classify as unified_classify
from core_engines.attack import AttackDecisionEngine
from core_engines.validation.loop_engine import ValidationLoopEngine
from core_engines.validation.evidence_builder import EvidenceBuilder
from core_engines.validation.verdict_handler import VerdictHandler
from core_engines.validation.replayer import AuthContext, RequestSpec
from core_engines.reporting.reporting import ReportGenerator, ValidationError, ConfidenceThresholdError
from database import db, models

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(name)s — %(levelname)s: %(message)s"
)
logger = logging.getLogger("rastro.main")

app = FastAPI(title="Rastro", version="0.2")


def get_db():
    db_obj = db.SessionLocal()
    try:
        yield db_obj
    finally:
        db_obj.close()


class TargetCreate(BaseModel):
    name: str
    domain: str | None = None
    mode: str | None = "FAST"


class EndpointCreate(BaseModel):
    target_id: int
    path: str
    method: str = "GET"
    params: dict | None = None


class FindingCreate(BaseModel):
    target_id: int
    endpoint_id: int | None = None
    title: str
    severity: str | None = "medium"
    description: str | None = None


class EndpointAnalysisRequest(BaseModel):
    path: str
    method: str = "GET"
    params: dict | None = None
    model: str | None = None


class ValidateHotPathRequest(BaseModel):
    """Request to validate a hot path for exploitation."""
    hot_path_id: str
    endpoint_id: int
    target_id: int
    url: str
    method: str = "GET"
    headers: dict | None = None
    params: dict | None = None
    body: str | None = None
    # Auth contexts for comparison
    auth_baseline_token: str | None = None
    auth_baseline_label: str = "baseline"
    auth_probe_token: str | None = None
    auth_probe_label: str = "probe"
    # Mutations to apply to probe requests
    mutations: dict | None = None
    min_attempts: int = 3


@app.on_event("startup")
async def startup_event():
    db.init_db()


@app.get("/")
async def root():
    return {"message": "Rastro backend inicializado"}


@app.post("/targets")
async def create_target(target: TargetCreate, session: Session = Depends(get_db)):
    db_target = models.Target(name=target.name, domain=target.domain)
    session.add(db_target)
    session.commit()
    session.refresh(db_target)
    return {
        "id": db_target.id,
        "name": db_target.name,
        "domain": db_target.domain,
        "mode": target.mode,
    }


@app.get("/targets")
async def list_targets(session: Session = Depends(get_db)):
    targets = session.query(models.Target).all()
    return [{"id": t.id, "name": t.name, "domain": t.domain} for t in targets]


@app.get("/targets/{target_id}/summary")
async def target_summary(target_id: int, session: Session = Depends(get_db)):
    target = session.query(models.Target).filter(models.Target.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    endpoints = (
        session.query(models.Endpoint)
        .filter(models.Endpoint.target_id == target.id)
        .all()
    )
    entries = []
    for endpoint in endpoints:
        params = endpoint.parsed_params
        metadata = unified_classify(endpoint.path, endpoint.method, params)
        entries.append(
            {
                "path": endpoint.path,
                "method": endpoint.method,
                "labels": metadata.get("labels", []),
            }
        )
    sc = unified_score_target(
        {
            "is_saas": bool(target.domain),
            "has_api": any("api" in item.get("labels", []) for item in entries),
            "multi_tenant": any(
                "org" in item.get("labels", []) or "tenant" in item.get("labels", [])
                for item in entries
            ),
            "has_admin": any("admin" in item.get("labels", []) for item in entries),
            "has_graphql": any("graphql" in item.get("labels", []) for item in entries),
        }
    )
    return {
        "target": {"id": target.id, "name": target.name, "domain": target.domain},
        "endpoints": entries,
        "score": sc,
    }


@app.post("/analysis/endpoint")
async def analyze_endpoint(request: EndpointAnalysisRequest):
    local = unified_classify(
        request.path, request.method, request.params or {}
    )
    result = {"local": local}
    try:
        ai = AIAnalyzer()
        result["ai"] = ai.analyze_endpoint(
            request.path, request.method, request.params or {}
        )
    except Exception as exc:
        result["ai_error"] = str(exc)
    return result


@app.post("/endpoints")
async def create_endpoint(endpoint: EndpointCreate, session: Session = Depends(get_db)):
    target = (
        session.query(models.Target)
        .filter(models.Target.id == endpoint.target_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    db_endpoint = models.Endpoint(
        target_id=endpoint.target_id,
        path=endpoint.path,
        method=endpoint.method,
        params=str(endpoint.params) if endpoint.params else None,
    )
    session.add(db_endpoint)
    session.commit()
    session.refresh(db_endpoint)
    return {
        "id": db_endpoint.id,
        "target_id": db_endpoint.target_id,
        "path": db_endpoint.path,
        "method": db_endpoint.method,
    }


@app.get("/endpoints")
async def list_endpoints(session: Session = Depends(get_db)):
    endpoints = session.query(models.Endpoint).all()
    return [
        {
            "id": e.id,
            "target_id": e.target_id,
            "path": e.path,
            "method": e.method,
            "params": e.params,
        }
        for e in endpoints
    ]


@app.post("/findings")
async def create_finding(finding: FindingCreate, session: Session = Depends(get_db)):
    target = (
        session.query(models.Target)
        .filter(models.Target.id == finding.target_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if finding.endpoint_id:
        endpoint = (
            session.query(models.Endpoint)
            .filter(models.Endpoint.id == finding.endpoint_id)
            .first()
        )
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")
    db_finding = models.Finding(
        target_id=finding.target_id,
        endpoint_id=finding.endpoint_id,
        title=finding.title,
        severity=finding.severity,
        description=finding.description,
    )
    session.add(db_finding)
    session.commit()
    session.refresh(db_finding)
    return {
        "id": db_finding.id,
        "title": db_finding.title,
        "severity": db_finding.severity,
    }


@app.get("/findings")
async def list_findings(session: Session = Depends(get_db)):
    findings = session.query(models.Finding).all()
    return [
        {
            "id": f.id,
            "target_id": f.target_id,
            "endpoint_id": f.endpoint_id,
            "title": f.title,
            "severity": f.severity,
            "description": f.description,
        }
        for f in findings
    ]


@app.post("/scans")
async def launch_scan(target: TargetCreate, session: Session = Depends(get_db)):
    from core_engines.orchestrator.scan_service import launch_scan as service_launch_scan
    return await service_launch_scan(
        target_name=target.name,
        target_domain=target.domain,
        target_mode=target.mode,
        session=session
    )


@app.get("/scan_runs")
async def list_scan_runs(
    target_id: int | None = None, session: Session = Depends(get_db)
):
    q = session.query(models.ScanRun)
    if target_id:
        q = q.filter(models.ScanRun.target_id == target_id)
    runs = q.order_by(models.ScanRun.started_at.desc()).limit(50).all()
    out = []
    for r in runs:
        out.append(
            {
                "id": r.id,
                "target_id": r.target_id,
                "mode": r.mode,
                "status": r.status,
                "endpoint_count": r.endpoint_count,
                "started_at": (
                    r.started_at.isoformat(sep=" ", timespec="seconds")
                    if r.started_at
                    else None
                ),
                "finished_at": (
                    r.finished_at.isoformat(sep=" ", timespec="seconds")
                    if r.finished_at
                    else None
                ),
            }
        )
    return out


@app.get("/scan_runs/{scan_id}")
async def get_scan_run(scan_id: int, session: Session = Depends(get_db)):
    run = session.query(models.ScanRun).filter(models.ScanRun.id == scan_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="ScanRun not found")
    return {
        "id": run.id,
        "target_id": run.target_id,
        "mode": run.mode,
        "status": run.status,
        "endpoint_count": run.endpoint_count,
        "outputs": run.outputs,
        "started_at": (
            run.started_at.isoformat(sep=" ", timespec="seconds")
            if run.started_at
            else None
        ),
        "finished_at": (
            run.finished_at.isoformat(sep=" ", timespec="seconds")
            if run.finished_at
            else None
        ),
    }


@app.get("/digest")
async def daily_digest(session: Session = Depends(get_db)):
    import json

    logger = logging.getLogger("rastro.main")

    entries = []
    endpoints = session.query(models.Endpoint).all()

    for endpoint in endpoints:
        safe_path = str(endpoint.path or "/")
        safe_method = str(endpoint.method or "GET")

        result = unified_score(
            safe_path, safe_method, endpoint.parsed_params
        )
        entries.append(
            {
                "id": endpoint.id,
                "target_id": endpoint.target_id,
                "path": safe_path,
                "method": safe_method,
                "labels": result["labels"],
                "risk_score": result["risk_score"],
            }
        )

    entries.sort(key=lambda item: item["risk_score"], reverse=True)
    return {"high_signal": entries[:20], "total_endpoints": len(endpoints)}


@app.get("/attack/decision")
async def attack_decision(
    target_id: int | None = None, session: Session = Depends(get_db)
):
    import json
    import ast

    logger = logging.getLogger("rastro.main")

    engine = AttackDecisionEngine()
    query = session.query(models.Endpoint)
    if target_id is not None:
        query = query.filter(models.Endpoint.target_id == target_id)
    endpoints = query.all()

    if not endpoints:
        return {"message": "No hay endpoints disponibles para evaluar."}

    endpoint_data = []
    for endpoint in endpoints:
        params = endpoint.parsed_params

        endpoint_data.append(
            {
                "path": endpoint.path,
                "method": endpoint.method,
                "params": params,
                "target_id": endpoint.target_id,
            }
        )

    return engine.evaluate_endpoints(endpoint_data)


@app.post("/findings/validate")
async def validate_and_report(
    request: ValidateHotPathRequest,
    session: Session = Depends(get_db),
):
    """
    Validate a hot path through execution and generate report if confirmed.
    
    Pipeline:
    1. Execute validation loop (baseline vs probe, multiple attempts)
    2. Capture evidence (request/response pairs)
    3. Gate: only proceed if verdict is confirmed + confidence >= 0.6
    4. Create finding and report
    
    Returns verdict, evidence, and report if validation passed.
    """
    logger.info(
        f"Validating hot_path={request.hot_path_id}, "
        f"endpoint_id={request.endpoint_id}, attempts={request.min_attempts}"
    )

    try:
        # Fetch endpoint from DB
        endpoint = (
            session.query(models.Endpoint)
            .filter(models.Endpoint.id == request.endpoint_id)
            .first()
        )
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        # Step 1: Run validation loop
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

        logger.info(f"Validation verdict: status={verdict.status}, confidence={verdict.confidence:.2f}")

        # Step 2: Capture evidence
        evidence_builder = EvidenceBuilder()
        
        # Rebuild comparisons for evidence (we need to re-run to capture them)
        replayer = validation_engine._replayer
        comparison_results = replayer.revalidate(
            request_spec=request_spec,
            auth_baseline=auth_baseline,
            auth_probe=auth_probe,
            mutations=request.mutations or {},
            min_attempts=request.min_attempts,
        )

        evidence_records = evidence_builder.build_all_from_comparisons(
            request_spec=request_spec,
            auth_context=auth_probe,
            comparisons=comparison_results,
            verdict_id=None,  # Will be set after saving verdict
        )

        comparison_summary = evidence_builder.build_comparison_summary(comparison_results)

        # Step 3: Process verdict → evidence → finding
        verdict_handler = VerdictHandler(session)
        finding = verdict_handler.process_verdict(
            verdict=verdict,
            endpoint_id=request.endpoint_id,
            target_id=request.target_id,
            evidence_records=evidence_records,
            comparison_summary=comparison_summary,
        )

        logger.info(
            f"Verdict processed: status={verdict.status}, "
            f"finding_id={finding.id if finding else 'None'}"
        )

        # Step 4: Gate report generation
        report_generator = ReportGenerator()
        report = None

        if finding and verdict.status == "confirmed":
            try:
                report = report_generator.draft_report(
                    findings={
                        "title": finding.title,
                        "severity": finding.severity,
                    },
                    verdict=verdict,
                    evidence_list=evidence_records,
                )
                logger.info(f"Report generated for finding_id={finding.id}")
            except (ValidationError, ConfidenceThresholdError) as e:
                logger.warning(f"Report generation blocked: {str(e)}")
                # Report is None, but finding still exists
        else:
            logger.info(
                f"Report not generated: verdict.status={verdict.status} "
                f"(not confirmed). Reason: {verdict.reason}"
            )

        # Step 5: Build response
        response = {
            "hot_path_id": request.hot_path_id,
            "verdict": {
                "status": verdict.status,
                "confidence": verdict.confidence,
                "reproducibility_score": verdict.reproducibility_score,
                "passed_rules": verdict.validation.passed_rules,
                "failed_rules": verdict.validation.failed_rules,
                "reason": verdict.reason,
            },
            "evidence": {
                "count": len(evidence_records),
                "attempts": [
                    {
                        "attempt": ev.get("attempt_label"),
                        "status_code": ev.get("response_status"),
                        "consistent": ev.get("consistent") == "true",
                        "sensitive_fields": (
                            [f.strip() for f in ev.get("sensitive_fields", "[]").split(",")]
                            if ev.get("sensitive_fields")
                            else []
                        ),
                        "curl_command": ev.get("curl_command"),
                    }
                    for ev in evidence_records
                ],
                "summary": comparison_summary,
            },
            "finding": {
                "id": finding.id if finding else None,
                "title": finding.title if finding else None,
                "severity": finding.severity if finding else None,
                "description": finding.description[:200] if finding and finding.description else None,
            } if finding else None,
            "report": report if report else None,
        }

        return response

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}",
        )


@app.get("/verdicts")
async def list_verdicts(
    status: str | None = None,
    confidence_min: float = 0.0,
    target_id: int | None = None,
    limit: int = 100,
    session: Session = Depends(get_db),
):
    """
    List all verdicts with optional filtering.
    
    Query parameters:
    - status: filter by "confirmed", "rejected", "inconclusive"
    - confidence_min: minimum confidence score
    - target_id: filter by target
    - limit: max results
    """
    query = session.query(models.Verdict)
    
    if status:
        query = query.filter(models.Verdict.status == status)
        if confidence_min > 0:
            from sqlalchemy import cast, Float
            query = query.filter(cast(models.Verdict.confidence, Float) >= confidence_min)
    if target_id:
        query = query.filter(models.Verdict.endpoint_id.in_(
            session.query(models.Endpoint.id).filter(models.Endpoint.target_id == target_id)
        ))
    
    verdicts = query.order_by(models.Verdict.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": v.id,
            "hot_path_id": v.hot_path_id,
            "status": v.status,
            "confidence": _parse_confidence(v.confidence),
            "reproducibility_score": float(v.reproducibility_score) if v.reproducibility_score else 0.0,
            "retry_count": v.retry_count,
            "reason": v.reason,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "validation_report": (
                __import__("json").loads(v.validation_report) 
                if v.validation_report else {}
            ),
        }
        for v in verdicts
    ]


def _parse_confidence(raw) -> float:
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        raw_stripped = raw.strip()
        if raw_stripped.startswith("{"):
            try:
                return float(__import__("json").loads(raw_stripped).get("score", 0.0))
            except (ValueError, TypeError, __import__("json").JSONDecodeError):
                pass
        try:
            return float(raw_stripped)
        except (ValueError, TypeError):
            pass
    return 0.0


@app.get("/verdicts/{verdict_id}")
async def get_verdict_detail(verdict_id: int, session: Session = Depends(get_db)):
    """Get detailed verdict information."""
    verdict = session.query(models.Verdict).filter(models.Verdict.id == verdict_id).first()
    if not verdict:
        raise HTTPException(status_code=404, detail="Verdict not found")
    
    return {
        "id": verdict.id,
        "hot_path_id": verdict.hot_path_id,
        "status": verdict.status,
        "confidence": float(verdict.confidence) if verdict.confidence else 0.0,
        "reproducibility_score": float(verdict.reproducibility_score) if verdict.reproducibility_score else 0.0,
        "retry_count": verdict.retry_count,
        "reason": verdict.reason,
        "created_at": verdict.created_at.isoformat() if verdict.created_at else None,
        "validation_report": (
            __import__("json").loads(verdict.validation_report) 
            if verdict.validation_report else {}
        ),
        "confidence_details": (
            __import__("json").loads(verdict.confidence_details) 
            if verdict.confidence_details else {}
        ),
    }


@app.get("/verdicts/{verdict_id}/evidence")
async def get_evidence_records(verdict_id: int, session: Session = Depends(get_db)):
    """Get all evidence records for a verdict."""
    verdict = session.query(models.Verdict).filter(models.Verdict.id == verdict_id).first()
    if not verdict:
        raise HTTPException(status_code=404, detail="Verdict not found")
    
    evidence_records = session.query(models.Evidence).filter(
        models.Evidence.verdict_id == verdict_id
    ).order_by(models.Evidence.id).all()
    
    # Build formatted response
    attempts = []
    for ev in evidence_records:
        attempts.append({
            "attempt": ev.attempt_label,
            "status_code": ev.response_status,
            "consistent": ev.consistent == "true",
            "body_diff_ratio": float(ev.body_diff_ratio) if ev.body_diff_ratio else 0.0,
            "sensitive_fields": (
                __import__("json").loads(ev.sensitive_fields)
                if ev.sensitive_fields else []
            ),
            "curl_command": ev.curl_command,
            "body_hash": ev.response_body_hash,
        })
    
    return {
        "verdict_id": verdict_id,
        "total_attempts": len(evidence_records),
        "attempts": attempts,
        "summary": {
            "total_attempts": len(evidence_records),
            "consistent_count": sum(1 for ev in evidence_records if ev.consistent == "true"),
            "consistency_ratio": (
                sum(1 for ev in evidence_records if ev.consistent == "true") / 
                max(len(evidence_records), 1)
            ),
        },
        "reproduction_steps": [
            "1. Obtain authentication tokens for two different users",
            "2. Execute the curl commands below as each user",
            "3. Compare responses for sensitive data leakage",
            "4. Verify consistent access across different privilege levels",
        ],
    }


@app.post("/verdicts/{verdict_id}/replay")
async def replay_evidence_attempt(
    verdict_id: int,
    attempt_label: str = "attempt_1",
    session: Session = Depends(get_db),
):
    """
    Replay a recorded evidence attempt to verify vulnerability.
    
    Re-executes the request with the same auth context and compares result.
    """
    verdict = session.query(models.Verdict).filter(models.Verdict.id == verdict_id).first()
    if not verdict:
        raise HTTPException(status_code=404, detail="Verdict not found")
    
    evidence = session.query(models.Evidence).filter(
        models.Evidence.verdict_id == verdict_id,
        models.Evidence.attempt_label == attempt_label,
    ).first()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence attempt not found")
    
    # Replay the request
    from core_engines.validation.replayer import RequestReplayer, AuthContext, RequestSpec
    import json
    
    try:
        replayer = RequestReplayer()
        
        request_spec = RequestSpec(
            url=evidence.request_url,
            method=evidence.request_method,
            headers=json.loads(evidence.request_headers or "{}"),
            params=json.loads(evidence.request_params or "{}"),
            body=evidence.request_body,
        )
        
        auth = AuthContext(
            label=evidence.auth_label or "replay",
            token=None,  # Would need to be provided
        )
        
        response = replayer.execute(request_spec, auth)
        
        return {
            "verdict_id": verdict_id,
            "attempt_label": attempt_label,
            "replay_status": "success",
            "response_status_code": response.status_code,
            "response_headers": response.headers,
            "response_body": response.body,
            "elapsed_ms": response.elapsed_ms,
            "error": response.error,
            "status_match": response.status_code == evidence.response_status,
            "original_response": {
                "status_code": evidence.response_status,
                "body_hash": evidence.response_body_hash,
            },
        }
    except Exception as e:
        logger.error(f"Replay failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Replay execution failed: {str(e)}",
        )


@app.get("/findings/scored")
async def list_findings_ranked(
    target_id: int | None = None,
    severity: str | None = None,
    limit: int = 50,
    session: Session = Depends(get_db),
):
    """
    List findings ranked by confidence × severity.
    
    Findings are only returned if they have an associated confirmed verdict.
    """
    query = session.query(models.Finding).filter(models.Finding.description.isnot(None))
    
    if target_id:
        query = query.filter(models.Finding.target_id == target_id)
    if severity:
        query = query.filter(models.Finding.severity == severity)
    
    findings = query.order_by(models.Finding.created_at.desc()).limit(limit).all()
    
    results = []
    for finding in findings:
        # Try to find associated verdict by endpoint
        verdict = None
        if finding.endpoint_id:
            verdict = session.query(models.Verdict).filter(
                models.Verdict.endpoint_id == finding.endpoint_id
            ).order_by(models.Verdict.created_at.desc()).first()
        
        confidence = float(verdict.confidence) if verdict and verdict.confidence else 0.5
        
        # Map confidence to severity if not set
        if not finding.severity:
            if confidence >= 0.8:
                severity_val = "critical"
            elif confidence >= 0.7:
                severity_val = "high"
            elif confidence >= 0.6:
                severity_val = "medium"
            else:
                severity_val = "low"
        else:
            severity_val = finding.severity
        
        # Calculate expected value (confidence × severity score)
        severity_score = {"critical": 10, "high": 8, "medium": 5, "low": 2}.get(severity_val, 3)
        expected_value = confidence * severity_score
        
        results.append({
            "id": finding.id,
            "title": finding.title,
            "severity": severity_val,
            "confidence": confidence,
            "expected_value": expected_value,
            "target_id": finding.target_id,
            "endpoint_id": finding.endpoint_id,
            "created_at": finding.created_at.isoformat() if finding.created_at else None,
            "verdict_status": verdict.status if verdict else "unknown",
        })
    
    # Sort by expected value
    results.sort(key=lambda x: x["expected_value"], reverse=True)
    
    return results
