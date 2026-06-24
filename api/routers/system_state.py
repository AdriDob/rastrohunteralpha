"""System state API endpoint — exposes global health + event history.

GET /api/system/state — Full system state summary
GET /api/system/state/events — Recent event bus history
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from core_engines.system_state import get_system_state
from core_engines.events.event_bus import get_event_bus
from core_engines.contracts.wrapper import wrap_list

router = APIRouter(prefix="/api/system-state", tags=["system"])


@router.get("/state")
def get_state():
    """Full system state summary with service health details."""
    state = get_system_state()
    return {
        "state": state.get_summary(),
        "services": state.get_services(),
    }


@router.get("/state/events")
def get_state_events(
    event_type: str = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=200),
):
    """Recent event bus history."""
    bus = get_event_bus()
    events = bus.get_history(event_type=event_type, limit=limit)
    return {
        "events": events,
        "total": len(events),
    }
