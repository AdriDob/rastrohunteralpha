"""
Rastro Advisor — strategic responses to user queries.

Answers questions using real system data and rule-based logic.
Optional LLM enhancement falls back gracefully.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.ai.context_builder import build_full_context
from core.ai.insights import generate_insights
from core.ai.recommendations import generate_recommendations
from core.ai.provider import get_provider


def answer_query(query: str) -> Dict[str, Any]:
    query_lower = query.lower().strip()
    ctx = build_full_context()
    provider = get_provider()

    # Try LLM first
    if provider.is_available() and provider.name != "local/rule-based":
        try:
            system_prompt = _build_system_prompt(ctx)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ]
            llm_response = provider.chat(messages, max_tokens=600)
            if llm_response:
                return {
                    "answer": llm_response,
                    "source": provider.name,
                    "context_summary": _summarize_context(ctx),
                }
        except Exception:
            pass

    # Fallback to rule-based answers
    return {
        "answer": _rule_based_answer(query_lower, ctx),
        "source": "local/rules",
        "context_summary": _summarize_context(ctx),
    }


def _build_system_prompt(ctx: Dict[str, Any]) -> str:
    e = ctx.get("endpoints", {})
    t = ctx.get("targets", {})
    f = ctx.get("findings", {})
    v = ctx.get("verdicts", {})
    p = ctx.get("pipeline", {})
    o = ctx.get("opportunities", {})
    a = ctx.get("activity", {})
    qw = ctx.get("quick_wins", {})

    return f"""
Eres Rastro AI, el analista principal de un sistema de bug bounty intelligence.
Usa datos reales del sistema para responder. Sé breve, directo y accionable.

Contexto actual del sistema:
- Targets: {t.get('total', 0)}
- Endpoints: {e.get('total', 0)} ({e.get('high_signal', 0)} high signal, {e.get('actionable', 0)} accionables)
- Risk promedio: {e.get('avg_risk', 0)}
- Findings: {f.get('total', 0)} ({f.get('new_24h', 0)} en 24h)
- Veredictos: {v.get('total', 0)} ({v.get('confirmed', 0)} confirmados)
- Pipeline: {p.get('detected', 0)}D → {p.get('validated', 0)}V → {p.get('confirmed', 0)}C
- Oportunidades: {o.get('total', 0)} targets con ROI calculado
- Actividad 24h: {a.get('last_24h', 0)} eventos
- Scans activos: {ctx.get('scans', {}).get('active', 0)}
- Programas: {ctx.get('intelligence', {}).get('total_programs', 0)}
- Quick Wins: {qw.get('total_opportunities', 0)} oportunidades · score {qw.get('avg_quick_win_score', 0)} · valor total ${qw.get('total_estimated_value', 0):,.0f}

Reglas:
1. Responde solo con datos reales del contexto.
2. Si no sabes algo, dilo.
3. Prioriza recomendaciones accionables.
4. Incluye métricas relevantes.
5. Responde en español o inglés según el idioma de la pregunta.
"""


def _rule_based_answer(query: str, ctx: Dict[str, Any]) -> str:
    # ROI question
    if any(w in query for w in ["roi", "mejor target", "mejor oportunidad", "qué target", "best target", "what to attack"]):
        opps = ctx.get("opportunities", {}).get("top", [])
        if opps:
            best = opps[0]
            return (
                f"RECOMENDACIÓN: Atacar {best['name']}.\n\n"
                f"Motivos:\n"
                f"ROI {best['roi_score']:.0f} · Prioridad {best['priority']:.0f}\n"
                f"{best['ep_count']} endpoints · Calidad {best['quality']:.0f}\n\n"
                f"Tiempo estimado: {best['ep_count'] * 15} minutos\n"
                f"Valor esperado: ${best['priority'] * 100:,.0f}"
            )
        return "No hay targets con ROI calculado todavía. Agrega targets y ejecuta escaneos."

    # What changed
    if any(w in query for w in ["cambió", "cambio", "changed", "nuevo", "new", "reciente", "recent"]):
        activity = ctx.get("activity", {})
        events = activity.get("events", [])
        new_eps = ctx.get("endpoints", {}).get("discovered_24h", 0)
        new_findings = ctx.get("findings", {}).get("new_24h", 0)
        lines = []
        if new_eps > 0:
            lines.append(f"{new_eps} nuevos endpoints descubiertos")
        if new_findings > 0:
            lines.append(f"{new_findings} nuevos findings")
        if events:
            lines.append(f"{len(events)} eventos de actividad reciente")
        if not lines:
            return "No hay cambios significativos en las últimas 24 horas."
        return "Cambios recientes:\n- " + "\n- ".join(lines)

    # Quick wins
    if any(w in query for w in ["quick win", "rápido", "two hours", "dos horas", "completar"]):
        qw = ctx.get("quick_wins", {})
        top = qw.get("top_opportunities", [])
        cats = qw.get("categories", {})
        if top:
            lines = [f"{o['endpoint']} — score {o['score']:.2f} ({o['category']}) · ${o['payout']:,.0f} en {o['effort']}min" for o in top]
            header = f"Quick Wins ({qw.get('total_opportunities', 0)} oportunidades, valor total ${qw.get('total_estimated_value', 0):,.0f}):"
            cat_line = " · ".join(f"{k}: {v}" for k, v in sorted(cats.items())) if cats else ""
            return header + "\n" + ("\n".join(lines)) + ("\n" + cat_line if cat_line else "")
        return "No hay quick wins disponibles. Agrega targets y ejecuta escaneos."

    # Scan status
    if any(w in query for w in ["scan", "escaneo", "terminó", "running", "ejecutando"]):
        scans = ctx.get("scans", {}).get("recent", [])
        if scans:
            lines = []
            for s in scans[:5]:
                status_icon = {"completed": "✅", "running": "🔄", "pending": "⏳", "failed": "❌", "timeout": "⚠️"}.get(s.get("status", ""), "❓")
                lines.append(f"{status_icon} Scan #{s['id']} modo {s.get('mode','?')}: {s.get('status','?')} ({s.get('endpoint_count',0)} endpoints)")
            return "Últimos escaneos:\n" + "\n".join(lines)
        return "No hay escaneos registrados aún."

    # Best platform
    if any(w in query for w in ["plataforma", "platform", "programa", "program", "resultados"]):
        intel = ctx.get("intelligence", {})
        platforms = intel.get("platforms", {})
        if platforms:
            best = max(platforms, key=platforms.get)
            return f"Mejor plataforma: {best} ({platforms[best]} programas activos). Total: {intel.get('total_programs', 0)} programas."
        return "No hay datos de inteligencia de programas todavía."

    # Default
    e = ctx.get("endpoints", {})
    t = ctx.get("targets", {})
    p = ctx.get("pipeline", {})
    return (
        f"Resumen del sistema:\n"
        f"• {t.get('total', 0)} targets · {e.get('total', 0)} endpoints\n"
        f"• {e.get('high_signal', 0)} high signal · riesgo promedio {e.get('avg_risk', 0)}\n"
        f"• Pipeline: {p.get('detected', 0)}D → {p.get('validated', 0)}V → {p.get('confirmed', 0)}C\n"
        f"• {ctx.get('opportunities', {}).get('total', 0)} oportunidades calculadas\n\n"
        f"Pregúntame sobre: ROI, cambios recientes, quick wins, "
        f"estado de escaneos, mejor plataforma, o qué hacer ahora."
    )


def _summarize_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "targets": ctx.get("targets", {}).get("total", 0),
        "endpoints": ctx.get("endpoints", {}).get("total", 0),
        "high_signal": ctx.get("endpoints", {}).get("high_signal", 0),
        "findings": ctx.get("findings", {}).get("total", 0),
        "confirmed_verdicts": ctx.get("verdicts", {}).get("confirmed", 0),
        "pipeline": ctx.get("pipeline", {}),
        "opportunities": ctx.get("opportunities", {}).get("total", 0),
        "activity_24h": ctx.get("activity", {}).get("last_24h", 0),
    }
