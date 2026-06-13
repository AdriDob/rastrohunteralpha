from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.services.data_service import list_verdicts, get_verdict, get_evidence_for_verdict

router = APIRouter(prefix="/api/verdicts", tags=["verdicts"])


@router.get("")
def get_verdicts(
    status: Optional[str] = Query(None),
    confidence_min: float = Query(0.0, ge=0.0, le=1.0),
    target_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    return list_verdicts(status=status, confidence_min=confidence_min, target_id=target_id, limit=limit)


@router.get("/{verdict_id}")
def get_verdict_detail(verdict_id: int):
    v = get_verdict(verdict_id)
    if not v:
        raise HTTPException(status_code=404, detail="Verdict not found")
    return v


@router.get("/{verdict_id}/evidence")
def get_evidence(verdict_id: int):
    v = get_verdict(verdict_id)
    if not v:
        raise HTTPException(status_code=404, detail="Verdict not found")
    return get_evidence_for_verdict(verdict_id)
