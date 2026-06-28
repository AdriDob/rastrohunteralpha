
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from core_engines.intelligence.adaptive_memory import get_memory
from core_engines.intelligence.export import (
    export_history,
    export_recommendations,
    export_snapshots,
    export_trends,
)


def _fmt_validator(fmt: str) -> str:
    if fmt not in ("json", "csv", "markdown"):
        return "json"
    return fmt

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/analyze")
def analyze():
    memory = get_memory()
    history = memory.analyze()
    return history.to_dict()


@router.get("/history")
def get_history(
    fmt: str = Query("json"),
):
    memory = get_memory()
    history = memory.get_history()
    if history is None:
        history = memory.analyze()

    fmt = _fmt_validator(fmt)
    if fmt == "json":
        return history.to_dict()
    return PlainTextResponse(export_history(history, fmt))


@router.get("/trends")
def get_trends(
    fmt: str = Query("json"),
):
    memory = get_memory()
    trends = memory.detect_trends()
    fmt = _fmt_validator(fmt)
    if fmt == "json":
        return trends.to_dict()
    return PlainTextResponse(export_trends(trends, fmt))


@router.get("/recommendations")
def get_recommendations(
    fmt: str = Query("json"),
):
    memory = get_memory()
    recs = memory.recommend()
    fmt = _fmt_validator(fmt)
    if fmt == "json":
        return recs.to_dict()
    return PlainTextResponse(export_recommendations(recs, fmt))


@router.get("/snapshots")
def list_snapshots(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    fmt: str = Query("json"),
):
    memory = get_memory()
    snaps = memory.get_snapshots(limit=limit, offset=offset)
    fmt = _fmt_validator(fmt)
    if fmt == "json":
        return {"items": snaps, "total": len(snaps), "skip": offset, "limit": limit}
    return PlainTextResponse(export_snapshots(snaps, fmt))


@router.get("/snapshots/generate")
def generate_snapshot_endpoint(
    snapshot_type: str = Query("daily"),
):
    memory = get_memory()
    snap = memory.snapshot(snapshot_type)
    return snap.to_dict()


@router.get("/state")
def get_state():
    memory = get_memory()
    return memory.get_state()


@router.post("/refresh")
def refresh():
    memory = get_memory()
    history = memory.analyze()
    trends = memory.detect_trends()
    recs = memory.recommend()
    return {
        "analyzed": True,
        "history": history.to_dict(),
        "trends": trends.to_dict(),
        "recommendations": recs.to_dict(),
    }
