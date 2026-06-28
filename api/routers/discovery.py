"""Program discovery and technology fingerprinting API endpoints.

Extends the Hunter pipeline with catalog browsing, technology
distribution analytics, and on-demand program fetching.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core_engines.targets.hunter import Hunter

LOG = logging.getLogger("rastro.api.discovery")
router = APIRouter(prefix="/api/discovery", tags=["discovery"])


# ── Response schemas ─────────────────────────────────────────────────


class ProgramItem(BaseModel):
    id: int
    name: str
    domain: str | None = None
    source: str | None = None
    program_url: str | None = None
    quality_score: int | None = None
    roi_score: int | None = None
    opportunity_score: float | None = None
    technology_tags: list[str] = []
    cms_detected: str | None = None
    framework_detected: str | None = None
    wordpress_plugins_detected: list[str] = []
    saas_probability: float | None = None
    api_density: int | None = None
    graphql_detected: bool | None = None
    multi_tenant: bool | None = None
    admin_detected: bool | None = None
    tags: str | None = None
    created_at: str | None = None


class DiscoveryListResult(BaseModel):
    items: list[ProgramItem]
    total: int
    skip: int = 0
    limit: int = 100


class TechnologyDistribution(BaseModel):
    technology: str
    count: int


class FetchResult(BaseModel):
    platform: str
    fetched: int
    imported: int


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/programs", response_model=DiscoveryListResult)
def list_discovered_programs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
    technology: str = Query("", max_length=100),
):
    """Browse the persistent program catalog with technology filtering."""
    h = Hunter()
    items, total = h.list_programs(
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        technology=technology,
    )
    return DiscoveryListResult(
        items=[ProgramItem(**i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/programs/{program_id}", response_model=ProgramItem)
def get_program_detail(program_id: int):
    """Return a single program with full technology metadata."""
    h = Hunter()
    items, _ = h.list_programs(skip=0, limit=1)
    for item in items:
        if item["id"] == program_id:
            return ProgramItem(**item)
    raise HTTPException(status_code=404, detail="Program not found")


@router.get("/technologies", response_model=list[TechnologyDistribution])
def get_technology_distribution():
    """Return aggregate technology counts across all programs."""
    h = Hunter()
    return [TechnologyDistribution(**d) for d in h.count_by_technology()]


@router.post("/fetch", response_model=list[FetchResult])
def fetch_public_programs(platforms: list[str] | None = None):
    """Fetch and import public programs from specified platforms.

    If no platforms specified, fetches from all supported platforms.
    """
    h = Hunter()
    if not platforms:
        platforms = list(Hunter.SUPPORTED_PLATFORMS)
    results = []
    for platform in platforms:
        if platform not in Hunter.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported platform '{platform}'. "
                       f"Supported: {Hunter.SUPPORTED_PLATFORMS}",
            )
        programs = h.fetch_public_programs(platform)
        imported = h.ingest_programs(programs)
        results.append(FetchResult(
            platform=platform,
            fetched=len(programs),
            imported=len(imported),
        ))
    return results
