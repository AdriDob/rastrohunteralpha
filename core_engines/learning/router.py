"""API router for Personal Learning Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from core_engines.auth.auth import verify_token
from core_engines.learning import (
    get_profile_service,
    get_event_tracker,
    get_prioritizer,
    get_explainer,
    get_memory_builder,
    get_exporter,
)

router = APIRouter(prefix="/api/learning", tags=["learning"])


# ─── Helpers ─────────────────────────────────────────────────────────────

def _get_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Not authenticated")
    data = verify_token(token)
    if data is None:
        raise HTTPException(401, "Invalid or expired token")
    return data.get("sub", "0")


# ─── Schemas ─────────────────────────────────────────────────────────────

class EventBody(BaseModel):
    event_type: str
    data: Dict[str, Any] = {}


class PrioritizeTargetsBody(BaseModel):
    targets: List[Dict[str, Any]]


class PrioritizeFindingsBody(BaseModel):
    findings: List[Dict[str, Any]]


class TargetContextBody(BaseModel):
    target: Dict[str, Any]


class PreferenceUpdate(BaseModel):
    adaptive_mode: Optional[bool] = None


# ─── Profile ─────────────────────────────────────────────────────────────

@router.get("/profile")
def get_profile(request: Request):
    user_id = _get_user_id(request)
    service = get_profile_service()
    stats = service.get_stats(user_id)
    return stats


@router.post("/profile/reset")
def reset_profile(request: Request):
    user_id = _get_user_id(request)
    service = get_profile_service()
    ok = service.reset(user_id)
    if not ok:
        get_profile_service().get_or_create(user_id)
    return {"ok": True}


# ─── Preferences ─────────────────────────────────────────────────────────

@router.patch("/preferences")
def update_preferences(body: PreferenceUpdate, request: Request):
    user_id = _get_user_id(request)
    service = get_profile_service()
    profile = service.get_or_create(user_id)
    if body.adaptive_mode is not None:
        profile.adaptive_mode = body.adaptive_mode
        service.save(profile)
    return {"ok": True}


# ─── Events ─────────────────────────────────────────────────────────────

@router.post("/events")
def track_event(body: EventBody, request: Request):
    """Generic event tracking endpoint."""
    user_id = _get_user_id(request)
    tracker = get_event_tracker()
    tracker._profile.log_event(user_id, body.event_type, body.data)

    # Route to specific tracker methods for automatic profile updates
    if body.event_type == "target_viewed":
        tracker.track_target_viewed(user_id, body.data)
    elif body.event_type == "finding_created":
        tracker.track_finding_created(user_id, body.data)
    elif body.event_type == "finding_validated":
        tracker.track_finding_validated(user_id, body.data)
    elif body.event_type == "session_started":
        tracker.track_session_started(user_id)
    elif body.event_type == "session_ended":
        tracker.track_session_ended(user_id, body.data.get("duration_minutes", 0))
    elif body.event_type == "module_visited":
        tracker.track_module_visited(user_id, body.data.get("module", ""))
    elif body.event_type == "tool_used":
        tracker.track_tool_used(user_id, body.data.get("tool", ""))

    return {"ok": True}


@router.get("/events")
def list_events(
    request: Request,
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
):
    user_id = _get_user_id(request)
    service = get_profile_service()
    events = service.get_events(user_id, event_type, limit)
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "data": e.data,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in events
    ]


# ─── Prioritization ──────────────────────────────────────────────────────

@router.post("/prioritize/targets")
def prioritize_targets(body: PrioritizeTargetsBody, request: Request):
    user_id = _get_user_id(request)
    prioritizer = get_prioritizer()
    results = prioritizer.prioritize_targets(user_id, body.targets)
    return [r.to_dict() for r in results]


@router.post("/prioritize/findings")
def prioritize_findings(body: PrioritizeFindingsBody, request: Request):
    user_id = _get_user_id(request)
    prioritizer = get_prioritizer()
    results = prioritizer.prioritize_findings(user_id, body.findings)
    return [r.to_dict() for r in results]


# ─── Explanations ────────────────────────────────────────────────────────

@router.post("/explain/priority")
def explain_priority(body: PrioritizeTargetsBody, request: Request):
    """Explain why targets are prioritised."""
    user_id = _get_user_id(request)
    explainer = get_explainer()
    results = []
    for t in body.targets:
        reasons = explainer.why_priority_increased(user_id, "target", t)
        results.append({"target": t, "explanations": reasons})
    return results


@router.get("/explain/profile-summary")
def profile_summary(request: Request):
    user_id = _get_user_id(request)
    explainer = get_explainer()
    return {"summary": explainer.profile_summary(user_id)}


# ─── AI Memory ───────────────────────────────────────────────────────────

@router.post("/memory/context")
def get_context(body: TargetContextBody, request: Request):
    user_id = _get_user_id(request)
    builder = get_memory_builder()
    context = builder.build_context(user_id, body.target)
    tips = builder.investigation_tip(user_id, body.target)
    return {"context": context, "tip": tips}


@router.get("/memory/similar-findings")
def similar_findings(request: Request, bug_class: str = Query("")):
    user_id = _get_user_id(request)
    builder = get_memory_builder()
    return builder.find_similar_findings(user_id, bug_class)


# ─── Daily Recommendations ──────────────────────────────────────────────

@router.get("/recommendations/daily")
def daily_recommendations(request: Request):
    user_id = _get_user_id(request)
    prioritizer = get_prioritizer()
    return prioritizer.daily_summary_recommendations(user_id)


# ─── Export ──────────────────────────────────────────────────────────────

@router.get("/export")
def export_profile(request: Request, fmt: str = Query("json", pattern="^(json|markdown)$")):
    user_id = _get_user_id(request)
    exporter = get_exporter()
    content = exporter.export(user_id, fmt)
    media = "application/json" if fmt == "json" else "text/markdown"
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content, media_type=media)
