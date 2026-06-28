"""API endpoints for the Multi-Agent system — persistent pipelines with full traceability."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core_engines.agents import (
    AgentEvent,
    EventType,
    get_agent_bus,
    get_all_agents,
    get_coordinator,
    get_financial_agent,
    get_memory_agent,
    get_strategy_agent,
)

logger = logging.getLogger("rastro.api.agents")
router = APIRouter(prefix="/api/agents", tags=["agents"])


# ── Health & Agent Status ─────────────────────────────────────────


@router.get("/health")
def get_agents_health() -> dict[str, Any]:
    """Get health status for all agents."""
    return {
        "agents": {a.agent_id.value: a.health() for a in get_all_agents()},
    }


# ── Persistent Pipeline Management ────────────────────────────────


@router.get("/pipelines")
def list_all_pipelines(status: str = "", limit: int = 50) -> dict[str, Any]:
    """List all pipelines, optionally filtered by status. Reads from SQLite."""
    coordinator = get_coordinator()
    pipelines = coordinator.list_pipelines()
    result = []
    for pid, info in pipelines.items():
        if status and info.get("state") != status:
            continue
        result.append({
            "id": pid,
            "target_id": info.get("target_id"),
            "target_name": info.get("target_name", "unknown"),
            "state": info.get("state", "unknown"),
            "retries": info.get("retries", 0),
            "quality_score": round(info.get("quality_score", 0.0), 2),
            "stages": info.get("stages", []),
            "error": info.get("error", ""),
            "created_at": info.get("created_at", ""),
        })
    return {
        "pipelines": sorted(result, key=lambda p: p["created_at"], reverse=True)[:limit],
        "total": len(result),
    }


@router.get("/pipelines/{pipeline_id}")
def get_pipeline_detail(pipeline_id: str) -> dict[str, Any]:
    """Get detailed pipeline status including full transition history."""
    coordinator = get_coordinator()
    status = coordinator.get_pipeline_status(pipeline_id)
    if not status:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"pipeline": status}


@router.post("/pipeline/start")
def start_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
    """Start a new autonomous pipeline for a target."""
    bus = get_agent_bus()
    target_id = payload.get("target_id", 0)
    target_name = payload.get("target_name", "")

    if not target_id and not target_name:
        raise HTTPException(status_code=400, detail="target_id or target_name required")

    event = AgentEvent(
        event_type=EventType.PIPELINE_START,
        source="api",
        target="coordinator",
        payload={"target_id": target_id, "target_name": target_name},
    )
    bus.publish(event)
    logger.info("[API] Pipeline started for target %s (corr=%s)",
                target_name, event.correlation_id[:8])
    return {"status": "started", "correlation_id": event.correlation_id, "target": target_name}


@router.post("/pipelines/{pipeline_id}/cancel")
def cancel_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Cancel an active pipeline."""
    bus = get_agent_bus()
    coordinator = get_coordinator()
    info = coordinator.get_pipeline_status(pipeline_id)
    if not info:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    event = AgentEvent(
        event_type=EventType.PIPELINE_CANCELLED,
        source="api",
        target="coordinator",
        payload={"pipeline_id": pipeline_id},
        correlation_id=pipeline_id,
    )
    bus.publish(event)
    return {"status": "cancelled", "pipeline_id": pipeline_id}


@router.delete("/pipelines/{pipeline_id}")
def delete_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Delete a pipeline record (both cache and DB)."""
    coordinator = get_coordinator()
    deleted = coordinator.delete_pipeline(pipeline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"status": "deleted", "pipeline_id": pipeline_id}


# ── Coordinator ───────────────────────────────────────────────────


@router.get("/coordinator/pipelines")
def list_active_pipelines() -> dict[str, Any]:
    """Legacy endpoint: list currently active in-memory pipelines."""
    coordinator = get_coordinator()
    return {"pipelines": coordinator.list_pipelines()}


@router.get("/coordinator/pipelines/{pipeline_id}")
def get_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Legacy endpoint: get a specific pipeline."""
    coordinator = get_coordinator()
    status = coordinator.get_pipeline_status(pipeline_id)
    return {"pipeline": status} if status else {"error": "not found"}


# ── Strategy ──────────────────────────────────────────────────────


@router.get("/strategy/recommendations")
def get_recommendations(limit: int = 10) -> dict[str, Any]:
    """Get strategic recommendations."""
    strategy = get_strategy_agent()
    return {"recommendations": strategy.get_recommendations(limit=limit)}


# ── Memory ────────────────────────────────────────────────────────


@router.get("/memory/stats")
def get_memory_stats() -> dict[str, Any]:
    """Get memory agent statistics."""
    memory = get_memory_agent()
    return {"stats": memory.get_stats()}


@router.get("/memory/{namespace}")
def get_memory_namespace(namespace: str) -> dict[str, Any]:
    """Retrieve a memory namespace."""
    memory = get_memory_agent()
    return {"namespace": namespace, "data": memory.recall_all(namespace)}


# ── Financial ─────────────────────────────────────────────────────


@router.get("/financial/summary")
def get_financial_summary() -> dict[str, Any]:
    """Get financial summary."""
    financial = get_financial_agent()
    return financial.get_summary()


@router.post("/financial/metric")
def set_financial_metric(payload: dict[str, Any]) -> dict[str, Any]:
    """Set a financial metric."""
    key = payload.get("key", "")
    value = payload.get("value")
    if key and value is not None:
        get_financial_agent().set_metric(key, value)
        return {"status": "ok"}
    return {"status": "error", "message": "key and value required"}


@router.post("/financial/goal")
def add_financial_goal(payload: dict[str, Any]) -> dict[str, Any]:
    """Add a financial goal."""
    get_financial_agent().add_goal(payload)
    return {"status": "goal_added"}


# ── Event Bus ──────────────────────────────────────────────────────


@router.get("/events")
def get_events(event_type: str = "", limit: int = 50) -> dict[str, Any]:
    """Get recent agent bus events."""
    bus = get_agent_bus()
    events = bus.get_history(event_type=event_type or None, limit=limit)
    return {
        "events": [_event_to_dict(e) for e in events],
        "count": len(events),
    }


@router.get("/events/stream")
async def stream_events(request: Request) -> StreamingResponse:
    """SSE streaming of agent bus events in real-time."""
    bus = get_agent_bus()

    async def event_generator():
        last_index = len(bus.get_history())
        while True:
            if await request.is_disconnected():
                break
            events = bus.get_history()
            if len(events) > last_index:
                for e in events[last_index:]:
                    yield f"data: {json.dumps(_event_to_dict(e))}\n\n"
                last_index = len(events)
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/replay/{correlation_id}")
def replay_events(correlation_id: str) -> dict[str, Any]:
    """Replay all events for a given correlation_id (full traceability)."""
    bus = get_agent_bus()
    events = bus.replay(correlation_id)
    return {
        "correlation_id": correlation_id,
        "events": [_event_to_dict(e) for e in events],
        "count": len(events),
    }


# ── Helpers ────────────────────────────────────────────────────────


def _event_to_dict(e: Any) -> dict[str, Any]:
    return {
        "event_id": e.event_id,
        "event_type": e.event_type,
        "source": str(e.source),
        "target": str(e.target) if e.target else None,
        "correlation_id": e.correlation_id,
        "priority": e.priority,
        "timestamp": e.timestamp,
        "payload": e.payload,
    }
