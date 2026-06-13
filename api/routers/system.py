from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core_engines.timeline import build_timeline
from core_engines.replay import build_replay, list_replay_targets
from core_engines.confidence import audit_verdicts, audit_findings, audit_single
from core_engines.review_queue import build_review_queue

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/timeline")
def get_timeline(
    target_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None),
):
    timeline = build_timeline(
        target_id=target_id,
        limit=limit,
        offset=offset,
        event_type=event_type,
    )
    return timeline.to_dict()


@router.get("/replay")
def get_replay_list():
    targets = list_replay_targets()
    return {"targets": targets, "total": len(targets)}


@router.get("/replay/{target_id}")
def get_replay(target_id: int):
    try:
        replay = build_replay(target_id)
        return replay.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/confidence")
def get_confidence_audit(
    item_type: str = Query("verdict"),
    limit: int = Query(50, ge=1, le=200),
):
    if item_type == "verdict":
        report = audit_verdicts(limit=limit)
    else:
        report = audit_findings(limit=limit)
    return report.to_dict()


@router.get("/confidence/{item_type}/{item_id}")
def get_confidence_single(item_type: str, item_id: int):
    if item_type not in ("verdict", "finding"):
        raise HTTPException(status_code=400, detail="item_type must be 'verdict' or 'finding'")
    audit = audit_single(item_type, item_id)
    if audit is None:
        raise HTTPException(status_code=404, detail=f"{item_type} {item_id} not found")
    return audit.to_dict()


@router.get("/review")
def get_review_queue(limit: int = Query(100, ge=1, le=500)):
    queue = build_review_queue(limit=limit)
    return queue.to_dict()
