"""
Summary Engine — generates concise summaries of Rastro system state.

Used for daily digests, system status reports, and quick overviews.
"""

from __future__ import annotations

from typing import Any, Dict

from core_engines.ai.context_builder import build_full_context
from core_engines.ai.insights import generate_insights, get_top_insight
from core_engines.ai.recommendations import get_best_recommendation
from core_engines.ai.provider import get_provider


def daily_summary() -> Dict[str, Any]:
    ctx = build_full_context()
    insights = generate_insights()
    rec = get_best_recommendation()
    provider = get_provider()

    e = ctx.get("endpoints", {})
    t = ctx.get("targets", {})
    f = ctx.get("findings", {})
    v = ctx.get("verdicts", {})
    p = ctx.get("pipeline", {})
    a = ctx.get("activity", {})
    o = ctx.get("opportunities", {})
    qw = ctx.get("quick_wins", {})

    critical_insights = [i for i in insights if i.get("severity") == "critical"]
    high_insights = [i for i in insights if i.get("severity") == "high"]

    summary = (
        f"📊 **Resumen del Sistema**\n\n"
        f"**Cobertura:** {t.get('total', 0)} targets · {e.get('total', 0)} endpoints "
        f"({e.get('high_signal', 0)} high signal)\n"
        f"**Riesgo promedio:** {e.get('avg_risk', 0)} · "
        f"**Pipeline:** {p.get('detected', 0)}D → {p.get('validated', 0)}V → {p.get('confirmed', 0)}C\n"
        f"**Hallazgos:** {f.get('total', 0)} total · {f.get('new_24h', 0)} nuevos (24h)\n"
        f"**Veredictos:** {v.get('total', 0)} total · {v.get('confirmed', 0)} confirmados\n"
        f"**Oportunidades:** {o.get('total', 0)} targets con ROI calculado\n"
        f"**Quick Wins:** {qw.get('total_opportunities', 0)} oportunidades · "
        f"${qw.get('total_estimated_value', 0):,.0f} valor estimado\n"
        f"**Actividad 24h:** {a.get('last_24h', 0)} eventos\n\n"
    )

    if critical_insights:
        summary += f"🔴 **{len(critical_insights)} alertas críticas**\n"
        for ins in critical_insights[:3]:
            summary += f"- {ins['title']}\n"
        summary += "\n"

    if high_insights:
        summary += f"🟠 **{len(high_insights)} alertas altas**\n"
        for ins in high_insights[:3]:
            summary += f"- {ins['title']}\n"
        summary += "\n"

    if rec.get("type") != "no_recommendations":
        summary += (
            f"🎯 **Recomendación principal:**\n"
            f"Atacar {rec.get('target_name', '?')} · "
            f"Prioridad {rec.get('priority_score', 0):.0f} · "
            f"Tiempo estimado: {rec.get('estimated_time_minutes', 0)} min · "
            f"Payout estimado: ${rec.get('estimated_payout', 0):,}\n"
        )

    summary += f"\n🤖 Asistente: {provider.name}"

    return {
        "summary": summary,
        "stats": {
            "targets": t.get("total", 0),
            "endpoints": e.get("total", 0),
            "high_signal": e.get("high_signal", 0),
            "avg_risk": e.get("avg_risk", 0),
            "findings": f.get("total", 0),
            "new_findings_24h": f.get("new_24h", 0),
            "confirmed_verdicts": v.get("confirmed", 0),
            "pipeline_detected": p.get("detected", 0),
            "pipeline_validated": p.get("validated", 0),
            "pipeline_confirmed": p.get("confirmed", 0),
            "opportunities": o.get("total", 0),
            "activity_24h": a.get("last_24h", 0),
            "quick_wins": qw.get("total_opportunities", 0),
            "quick_wins_value": qw.get("total_estimated_value", 0),
        },
        "critical_insights": len(critical_insights),
        "high_insights": len(high_insights),
        "top_recommendation": rec.get("target_name", ""),
        "provider": provider.name,
    }


def system_status() -> Dict[str, Any]:
    ctx = build_full_context()
    return {
        "system": ctx.get("health", {}),
        "activity": {
            "last_24h": ctx.get("activity", {}).get("last_24h", 0),
            "new_endpoints": ctx.get("endpoints", {}).get("discovered_24h", 0),
            "new_findings": ctx.get("findings", {}).get("new_24h", 0),
        },
        "top_insight": get_top_insight(),
        "top_recommendation": get_best_recommendation(),
    }
