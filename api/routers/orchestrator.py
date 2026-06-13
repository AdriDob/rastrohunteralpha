from fastapi import APIRouter

from core_engines.gateway.schemas import ok
from core_engines.orchestrator.assistant_orchestrator import get_orchestrator

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


@router.get("/decisions")
async def get_decisions():
    orchestrator = get_orchestrator()
    return ok(orchestrator.get_decisions())


@router.get("/next-action")
async def get_next_action():
    orchestrator = get_orchestrator()
    actions = orchestrator.recommend_next_action(3)
    return ok({
        "actions": [a.to_dict() for a in actions],
        "count": len(actions),
    })


@router.get("/highlights")
async def get_highlights():
    orchestrator = get_orchestrator()
    highlights = orchestrator.highlight_ui_elements()
    return ok({"decisions": highlights})


@router.post("/suppress-noise")
async def suppress_noise():
    orchestrator = get_orchestrator()
    count = orchestrator.suppress_noise_items()
    return ok({"suppressed": count})
