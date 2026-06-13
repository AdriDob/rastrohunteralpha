"""
Rastro Insights — automatically generated from real system data.

Every insight is computed from live database queries and engine outputs.
No mock data. No placeholders.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.ai.context_builder import build_full_context


def generate_insights() -> List[Dict[str, Any]]:
    ctx = build_full_context()
    insights: List[Dict[str, Any]] = []

    # ── 1. New critical endpoints ──
    hs = ctx.get("endpoints", {}).get("top_high_signal", [])
    critical = [e for e in hs if e.get("risk_score", 0) >= 50]
    if critical:
        for ep in critical[:3]:
            insights.append({
                "type": "critical_endpoint",
                "severity": "critical",
                "title": f"Nuevo endpoint crítico: {ep['method']} {ep['path']}",
                "detail": f"Risk score {ep['risk_score']:.0f} · Vector: {ep.get('vector', '?')}",
                "score": ep["risk_score"],
                "action": "Revisar y validar este endpoint para explotación",
            })

    # ── 2. Targets with growing ROI ──
    opps = ctx.get("opportunities", {}).get("top", [])
    high_roi = [t for t in opps if t.get("roi_score", 0) >= 50]
    if high_roi:
        for tgt in high_roi[:3]:
            insights.append({
                "type": "high_roi_target",
                "severity": "high",
                "title": f"Target con alto ROI: {tgt['name']}",
                "detail": (
                    f"ROI {tgt['roi_score']:.0f} · Prioridad {tgt['priority']:.0f} · "
                    f"{tgt['ep_count']} endpoints · Calidad {tgt['quality']:.0f}"
                ),
                "score": tgt["roi_score"],
                "action": f"Analizar {tgt['name']} para encontrar vectores de ataque",
            })

    # ── 3. Findings near confirmation ──
    pipeline = ctx.get("pipeline", {})
    detected = pipeline.get("detected", 0)
    validated = pipeline.get("validated", 0)
    confirmed = pipeline.get("confirmed", 0)
    if validated > 0:
        insights.append({
            "type": "findings_near_confirmation",
            "severity": "high",
            "title": f"{validated} findings en validación, cerca de confirmación",
            "detail": f"Pipeline: {detected} detectados → {validated} validados → {confirmed} confirmados",
            "score": validated * 10,
            "action": "Revisar findings en estado validado y generar reportes",
        })

    # ── 4. Recommended attack (highest ROI target with most actionable endpoints) ──
    actionable = ctx.get("endpoints", {}).get("top_actionable", [])
    if actionable and opps:
        best_tgt = opps[0]
        tgt_actionable = [a for a in actionable if a.get("target_id") == best_tgt["id"]]
        insights.append({
            "type": "recommended_attack",
            "severity": "critical",
            "title": f"Ataque recomendado: {best_tgt['name']}",
            "detail": (
                f"ROI {best_tgt['roi_score']:.0f} · Prioridad {best_tgt['priority']:.0f} · "
                f"{len(tgt_actionable)} endpoints accionables"
            ),
            "score": best_tgt["priority"],
            "action": f"Iniciar validación contra {best_tgt['name']}",
        })

    # ── 5. Attack surface changes ──
    surfaces = ctx.get("endpoints", {}).get("attack_surfaces", {})
    if surfaces:
        top_surface = max(surfaces, key=surfaces.get)  # type: ignore[arg-type]
        insights.append({
            "type": "attack_surface_summary",
            "severity": "medium",
            "title": f"Superficie de ataque principal: {top_surface}",
            "detail": f"{surfaces[top_surface]} endpoints en esta categoría · {len(surfaces)} superficies totales",
            "score": surfaces[top_surface] * 5,
            "action": "Explorar la superficie de ataque dominante para encontrar vectores",
        })

    # ── 6. Quick wins (actionable endpoints with risk >= 25) ──
    quick_wins = [e for e in actionable if e.get("risk_score", 0) >= 25]
    if quick_wins:
        insights.append({
            "type": "quick_wins",
            "severity": "high",
            "title": f"{len(quick_wins)} quick wins disponibles",
            "detail": f"Endpoints accionables con riesgo ≥ 25 listos para ser validados",
            "score": len(quick_wins) * 15,
            "action": "Revisar la lista de endpoints accionables y comenzar validación",
        })

    # ── 7. New discoveries in last 24h ──
    new_eps = ctx.get("endpoints", {}).get("discovered_24h", 0)
    new_findings = ctx.get("findings", {}).get("new_24h", 0)
    if new_eps > 0 or new_findings > 0:
        parts = []
        if new_eps > 0:
            parts.append(f"{new_eps} nuevos endpoints")
        if new_findings > 0:
            parts.append(f"{new_findings} nuevos findings")
        insights.append({
            "type": "new_discoveries",
            "severity": "medium",
            "title": "Actividad reciente detectada",
            "detail": " y ".join(parts) + " en las últimas 24 horas",
            "score": new_eps * 5 + new_findings * 10,
            "action": "Revisar nuevos descubrimientos para priorizar análisis",
        })

    # ── 8. Active scans ──
    active = ctx.get("scans", {}).get("active", 0)
    if active > 0:
        insights.append({
            "type": "active_scans",
            "severity": "info",
            "title": f"{active} scan(s) en ejecución",
            "detail": "Escaneos activos descubriendo nuevos endpoints",
            "score": active * 10,
            "action": "Esperar a que los escaneos terminen para revisar resultados",
        })

    # ── 9. Confirmed verdicts ready for reporting ──
    confirmed_v = ctx.get("verdicts", {}).get("confirmed", 0)
    if confirmed_v > 0:
        insights.append({
            "type": "ready_for_reporting",
            "severity": "high",
            "title": f"{confirmed_v} veredictos confirmados listos para reportar",
            "detail": "Generar reportes con los hallazgos confirmados",
            "score": confirmed_v * 20,
            "action": "Ir a Reports y generar reportes para los veredictos confirmados",
        })

    # ── 10. Pipeline health ──
    total_pipeline = sum(pipeline.values())
    if total_pipeline > 0:
        conversion = (confirmed / max(detected, 1)) * 100
        insights.append({
            "type": "pipeline_health",
            "severity": "info",
            "title": f"Pipeline: {conversion:.0f}% tasa de conversión",
            "detail": f"{detected} detectados → {confirmed} confirmados en {total_pipeline} findings totales",
            "score": conversion,
            "action": "Optimizar pipeline si la tasa de conversión es baja",
        })

    insights.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "info": 3}.get(x.get("severity", "info"), 4))

    return insights


def get_top_insight() -> Dict[str, Any]:
    insights = generate_insights()
    if insights:
        return insights[0]
    return {
        "type": "no_insights",
        "severity": "info",
        "title": "No hay insights en este momento",
        "detail": "Agrega targets y ejecuta escaneos para generar datos",
        "score": 0,
        "action": "Agregar un nuevo target o ejecutar un scan",
    }
