
from fastapi import APIRouter, HTTPException, Query

from core_engines.confidence import audit_findings, audit_single, audit_verdicts
from core_engines.replay import build_replay, list_replay_targets
from core_engines.review_queue import build_review_queue
from core_engines.timeline import build_timeline

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/timeline")
def get_timeline(
    target_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: str | None = Query(None),
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
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/confidence")
def get_confidence_audit(
    item_type: str = Query("verdict"),
    limit: int = Query(50, ge=1, le=200),
):
    report = audit_verdicts(limit=limit) if item_type == "verdict" else audit_findings(limit=limit)
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


@router.get("/state")
def get_system_state():
    """Full system state summary with service health details."""
    from core_engines.system_state import get_system_state as _get_state
    state = _get_state()
    return {
        "state": state.get_summary(),
        "services": state.get_services(),
    }


@router.get("/state/events")
def get_system_state_events(
    event_type: str = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=200),
):
    """Recent event bus history."""
    from core_engines.events.event_bus import get_event_bus
    bus = get_event_bus()
    events = bus.get_history(event_type=event_type, limit=limit)
    return {
        "events": events,
        "total": len(events),
    }


@router.get("/update-check")
def check_update():
    from desktop.updater import _current_version, check_for_updates
    release = check_for_updates()
    if release is None:
        return {"available": False, "current_version": _current_version()}
    return {
        "available": True,
        "version": release.version,
        "download_url": release.download_url,
        "release_notes_url": release.release_notes_url,
        "current_version": _current_version(),
    }
