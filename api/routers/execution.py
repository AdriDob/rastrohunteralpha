from fastapi import APIRouter

from core_engines.accountability.outcome_tracker import get_outcome_tracker
from core_engines.accountability.system_scorecard import get_system_scorecard
from core_engines.actions.action_engine import get_action_engine
from core_engines.actions.execution_tracker import get_execution_tracker
from core_engines.explainability.decision_trace import get_decision_trace
from core_engines.explainability.explanation_engine import get_explanation_engine
from core_engines.memory.decision_memory import get_decision_memory
from core_engines.memory.insight_archive import get_insight_archive

router = APIRouter(prefix="/api/execution", tags=["execution"])


@router.get("/tracker")
async def get_tracker():
    tracker = get_execution_tracker()
    return tracker.get_stats()


@router.get("/tracker/recent")
async def get_recent_executions(limit: int = 20):
    tracker = get_execution_tracker()
    return {"executions": tracker.get_recent(limit)}


@router.get("/actions")
async def list_actions():
    engine = get_action_engine()
    actions = engine.list_actions()
    return {"actions": [a.to_dict() for a in actions], "count": len(actions)}


@router.get("/actions/history")
async def get_action_history(limit: int = 20):
    engine = get_action_engine()
    return {"history": engine.get_history(limit)}


@router.get("/actions/stats")
async def get_action_stats():
    engine = get_action_engine()
    return engine.get_stats()


@router.get("/scorecard")
async def get_scorecard():
    scorecard = get_system_scorecard()
    metrics = scorecard.generate()
    return {
        "latest": metrics.to_dict(),
        "trend": scorecard.get_trend(),
        "history": scorecard.get_history(10),
    }


@router.get("/outcomes")
async def get_outcomes(limit: int = 20):
    tracker = get_outcome_tracker()
    return {
        "recent": tracker.get_recent(limit),
        "summary": tracker.get_summary(),
    }


@router.get("/explain")
async def get_explanations(limit: int = 20):
    engine = get_explanation_engine()
    return {
        "explanations": engine.list_recent(limit),
        "count": engine.count(),
    }


@router.get("/explain/{decision_id}")
async def get_explanation(decision_id: str):
    engine = get_explanation_engine()
    explanation = engine.get_explanation(decision_id)
    if explanation is None:
        return {"error": "Explanation not found", "version": "1.0"}
    return explanation.to_dict()


@router.get("/traces")
async def get_traces(limit: int = 20):
    collector = get_decision_trace()
    return {
        "traces": collector.list_recent(limit),
        "count": collector.count(),
    }


@router.get("/decisions")
async def get_decisions(limit: int = 50):
    memory = get_decision_memory()
    return {
        "decisions": memory.list_decisions(limit=limit),
        "count": memory.count_decisions(),
    }


@router.get("/insights")
async def get_insights(limit: int = 50):
    archive = get_insight_archive()
    return {
        "insights": archive.list_insights(limit=limit),
        "count": archive.total_count(),
        "by_type": archive.count_by_type(),
        "by_severity": archive.count_by_severity(),
    }


@router.get("/insights/source/{source}")
async def get_insights_by_source(source: str, limit: int = 20):
    archive = get_insight_archive()
    return {
        "insights": archive.recent_by_source(source, limit),
    }
