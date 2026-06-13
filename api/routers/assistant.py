"""
Rastro AI Assistant API endpoints.

All endpoints consume real system data through the Assistant module.
No mock data. No placeholders.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.ai.assistant import get_assistant
from core.assistant.ai_assistant import get_narrator

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class ChatRequest(BaseModel):
    message: str


@router.get("/context")
def get_context():
    assistant = get_assistant()
    return assistant.get_context()


@router.get("/insights")
def get_insights():
    assistant = get_assistant()
    items = assistant.get_insights()
    return {"insights": items, "count": len(items)}


@router.get("/insights/top")
def get_top_insight():
    assistant = get_assistant()
    return assistant.get_top_insight()


@router.get("/recommendations")
def get_recommendations():
    assistant = get_assistant()
    items = assistant.get_recommendations()
    return {"recommendations": items, "count": len(items)}


@router.get("/recommendations/best")
def get_best_recommendation():
    assistant = get_assistant()
    return assistant.get_best_recommendation()


@router.post("/chat")
def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    assistant = get_assistant()
    return assistant.chat(body.message)


@router.get("/summary")
def get_summary():
    assistant = get_assistant()
    return assistant.get_summary()


@router.get("/status")
def get_status():
    assistant = get_assistant()
    return assistant.get_status()


@router.get("/history")
def get_history(limit: int = Query(10, ge=1, le=50)):
    assistant = get_assistant()
    return {"history": assistant.get_history(limit)}


# ── Investigation Narrator endpoints ──

@router.get("/investigation/{target_id}")
def get_investigation_state(target_id: int):
    narrator = get_narrator()
    return narrator.explain_investigation_state(target_id)


@router.get("/narrative/{target_id}")
def get_report_narrative(target_id: int):
    narrator = get_narrator()
    return narrator.generate_report_narrative(target_id)


@router.get("/attack-path/{hot_path_id}")
def get_attack_path_explanation(hot_path_id: str):
    narrator = get_narrator()
    return narrator.explain_attack_path(hot_path_id)


@router.get("/unified/{target_id}")
def get_unified_reasoning(target_id: int):
    narrator = get_narrator()
    return narrator.unified_reasoning(target_id)


@router.get("/bounty/{target_id}")
def get_bounty_potential(target_id: int):
    narrator = get_narrator()
    return narrator.explain_bounty_potential(target_id)


@router.get("/briefing")
def get_daily_briefing():
    narrator = get_narrator()
    return narrator.generate_daily_briefing()


@router.get("/intelligence-report")
def get_system_intelligence_report():
    narrator = get_narrator()
    return narrator.generate_system_intelligence_report()
