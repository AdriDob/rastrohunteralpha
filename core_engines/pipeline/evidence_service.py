from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core_engines.pipeline.stages import PipelineContext, PipelineStage
from core_engines.validation.evidence_builder import EvidenceBuilder
from core_engines.validation.replayer import ComparisonResult, RequestSpec
from database import models


def collect_evidence(
    session: Session,
    ctx: PipelineContext,
    request_spec: RequestSpec,
    comparisons: List[ComparisonResult],
    verdict_id: int,
    auth_label: str = "baseline",
) -> PipelineContext:
    builder = EvidenceBuilder()
    records = builder.build_all_from_comparisons(
        request_spec=request_spec,
        auth_context=type("obj", (object,), {"label": auth_label})(),
        comparisons=comparisons,
        verdict_id=verdict_id,
    )

    evidence_ids = []
    for rec in records:
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
        session.add(db_ev)
        session.flush()
        evidence_ids.append(db_ev.id)

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
        session.add(db_vr)

    session.commit()
    ctx.evidence_ids = evidence_ids
    ctx.stage = PipelineStage.EVIDENCE_COLLECTED
    return ctx
