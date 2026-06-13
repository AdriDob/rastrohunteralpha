"""
Mission Control — Rastro's definitive Home.

Every widget consumes real API data. No placeholders. No mocks.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

try:
    import requests as http_requests
except ImportError:
    http_requests = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    px = None
    go = None

from database import db, models
from core.engine.unified_scoring import score as unified_score, generate_suggestions
from core.engine.risk_model import AttackSurfaceMapper, NoiseReductionLayer


def _api_get(url: str) -> Optional[Dict[str, Any]]:
    if not http_requests:
        return None
    try:
        r = http_requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _fetch_overview(backend_base: str) -> Optional[Dict[str, Any]]:
    return _api_get(f"{backend_base}/api/overview")


def _fetch_activity(backend_base: str, hours: int = 72) -> Optional[Dict[str, Any]]:
    return _api_get(f"{backend_base}/api/activity?hours={hours}")


def _fetch_intel(backend_base: str) -> Optional[Dict[str, Any]]:
    return _api_get(f"{backend_base}/api/intelligence/summary")


def _fetch_health(backend_base: str) -> Optional[Dict[str, Any]]:
    return _api_get(f"{backend_base}/api/system/health")


def _fetch_pipeline(backend_base: str) -> Optional[Dict[str, Any]]:
    return _api_get(f"{backend_base}/api/pipeline")


def _fetch_opportunities(backend_base: str) -> Optional[Dict[str, Any]]:
    return _api_get(f"{backend_base}/api/opportunities?limit=20&sort_by=roi&sort_order=desc")


def _fetch_attack_surfaces(backend_base: str) -> Optional[Dict[str, Any]]:
    return _api_get(f"{backend_base}/api/attack-surface")


def _fetch_digest(backend_base: str) -> Optional[Dict[str, Any]]:
    return _api_get(f"{backend_base}/api/digest")


def _fetch_quick_wins(backend_base: str) -> Optional[Dict[str, Any]]:
    if not http_requests:
        return None
    try:
        r = http_requests.post(f"{backend_base}/api/quick-wins/evaluate", json={}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _severity_color(s: str) -> str:
    return {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#3b82f6", "info": "#6b7280"}.get(s.lower(), "#6b7280")


def _severity_icon(s: str) -> str:
    return {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(s.lower(), "⚪")


def _metric_card(value, label, delta=None):
    delta_html = ""
    if delta is not None:
        cls = "delta-up" if delta > 0 else "delta-down"
        delta_html = f'<span class="{cls}">{"+" if delta > 0 else ""}{delta}</span>'
    return f"""
    <div class="metric-card">
      <div class="metric-value">{value}</div>
      <div class="metric-label">{label}</div>
      {delta_html}
    </div>
    """


MISSION_CONTROL_CSS = """
<style>
.mc-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 24px 0 8px 0;
}
.mc-header h1 {
  font-size: 26px; font-weight: 700; margin: 0;
  background: linear-gradient(135deg, #c084fc, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.mc-header p { color: #6b7280; font-size: 13px; margin: 2px 0 0 0; }
.mc-header-right { text-align: right; font-size: 12px; color: #6b7280; }

.metric-row {
  display: flex; gap: 12px; margin: 12px 0;
  flex-wrap: wrap;
}
.metric-card {
  background: #13161e; border: 1px solid #1e2230;
  border-radius: 10px; padding: 16px 20px; flex: 1; min-width: 140px;
  transition: border-color 0.15s;
}
.metric-card:hover { border-color: #a855f7; }
.metric-value {
  font-size: 28px; font-weight: 700; color: #e2e4e9; line-height: 1.1;
}
.metric-label { font-size: 12px; color: #6b7280; margin-top: 4px; }
.delta-up { color: #22c55e; font-size: 12px; margin-left: 6px; }
.delta-down { color: #ef4444; font-size: 12px; margin-left: 6px; }

.section-title {
  font-size: 15px; font-weight: 600; color: #e2e4e9; margin: 20px 0 10px 0;
  display: flex; align-items: center; gap: 8px;
}
.section-subtitle { font-size: 12px; color: #6b7280; margin: -6px 0 12px 0; }

.activity-item {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 8px 0; border-bottom: 1px solid #1a1e2a;
  font-size: 13px;
}
.activity-item:last-child { border-bottom: none; }
.activity-type-badge {
  font-size: 10px; font-weight: 600; padding: 2px 8px;
  border-radius: 4px; white-space: nowrap; min-width: 52px;
  text-align: center;
}
.activity-time { color: #6b7280; font-size: 11px; white-space: nowrap; }
.activity-detail { flex: 1; color: #c4c8d4; }

.intel-chip {
  display: inline-block; background: #1e2230; border-radius: 6px;
  padding: 6px 12px; margin: 3px; font-size: 12px; color: #c4c8d4;
}
</style>
"""


def render_mission_control(backend_base: str, use_backend: bool):
    st.markdown(MISSION_CONTROL_CSS, unsafe_allow_html=True)

    overview = _fetch_overview(backend_base) if use_backend else None

    if not overview:
        overview = _compute_overview_local()

    if not overview:
        st.error("No data available. Add targets and run scans first.")
        return

    now_str = datetime.now().strftime("%b %d, %Y %H:%M UTC")

    # ── Header ──
    st.markdown(f"""
    <div class="mc-header">
      <div>
        <h1>Mission Control</h1>
        <p>High signal. Low noise. Maximum impact.</p>
      </div>
      <div class="mc-header-right">{now_str}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Row 1: Metric Cards ──
    ov = overview
    cols = st.columns(6)
    metrics = [
        (str(ov.get("target_count", 0)), "Targets"),
        (str(ov.get("endpoint_count", 0)), "Endpoints"),
        (str(ov.get("high_signal_endpoints", 0)), "High Signal"),
        (str(ov.get("confirmed_verdicts", 0)), "Confirmed"),
        (str(ov.get("active_scans", 0)), "Active Scans"),
        (str(ov.get("avg_risk_score", 0)), "Avg Risk"),
    ]
    for i, (val, lbl) in enumerate(metrics):
        with cols[i]:
            st.markdown(
                f'<div class="metric-card"><div class="metric-value">{val}</div>'
                f'<div class="metric-label">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

    # ── Row 2: Pipeline Funnel + Risk Distribution ──
    st.markdown("<div class='section-title'>📊 Pipeline & Risk Overview</div>", unsafe_allow_html=True)
    col_pipe, col_risk = st.columns(2)

    with col_pipe:
        stages = ov.get("pipeline_stages", {})
        if px and stages:
            stage_names = ["Detected", "Validated", "Confirmed", "Reported"]
            stage_counts = [
                stages.get("detected", 0),
                stages.get("validated", 0),
                stages.get("confirmed", 0),
                stages.get("reported", 0),
            ]
            fig = go.Figure()
            fig.add_trace(go.Funnel(
                name="Pipeline",
                y=stage_names,
                x=stage_counts,
                textinfo="value+percent initial",
                marker={"color": ["#6366f1", "#8b5cf6", "#a855f7", "#c084fc"]},
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#c4c8d4", "size": 11},
                margin={"l": 40, "r": 20, "t": 10, "b": 10},
                height=220, showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Pipeline funnel requires plotly")

    with col_risk:
        rdist = ov.get("risk_distribution", {})
        if px and rdist:
            labels_r = list(rdist.keys())
            values_r = list(rdist.values())
            colors_r = ["#ef4444", "#f97316", "#eab308", "#3b82f6", "#6b7280"]
            fig = go.Figure(data=[go.Pie(
                labels=labels_r, values=values_r, hole=0.5,
                marker={"colors": colors_r},
                textinfo="label+percent", textfont={"size": 10, "color": "#c4c8d4"},
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#c4c8d4", "size": 11},
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                height=220, showlegend=False,
                annotations=[{"text": "Risk<br>Distribution", "font": {"size": 12, "color": "#6b7280"}, "showarrow": False}],
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Risk distribution requires plotly")

    # ── Row 3: Top Opportunities + Attack Vector Distribution ──
    st.markdown("<div class='section-title'>🎯 Top Opportunities</div>", unsafe_allow_html=True)
    col_opps, col_vec = st.columns([2, 1])

    with col_opps:
        opps = _fetch_opportunities(backend_base) if use_backend else None
        if opps and opps.get("items"):
            items = opps["items"][:10]
            if pd:
                df = pd.DataFrame(items)
                display_cols = [c for c in ["target_name", "type", "risk_score", "roi", "priority", "vector"] if c in df.columns]
                if display_cols:
                    st.dataframe(
                        df[display_cols],
                        use_container_width=True,
                        hide_index=True,
                        height=min(35 * len(items) + 38, 400),
                    )
            else:
                for item in items:
                    st.markdown(f"- **{item.get('target_name', '?')}** — risk={item.get('risk_score', '?')}, roi={item.get('roi', '?')}")
        else:
            st.caption("No opportunities found. Add targets to generate opportunities.")

    with col_vec:
        vdist = ov.get("vector_distribution", {})
        if px and vdist:
            labels_v = list(vdist.keys())
            values_v = list(vdist.values())
            fig = go.Figure(data=[go.Pie(
                labels=labels_v, values=values_v,
                marker={"colors": px.colors.qualitative.Set2},
                textinfo="label", textfont={"size": 9, "color": "#c4c8d4"},
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#c4c8d4", "size": 10},
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                height=220, showlegend=False,
                annotations=[{"text": "Attack<br>Vectors", "font": {"size": 11, "color": "#6b7280"}, "showarrow": False}],
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Vector distribution requires plotly")

    # ── Row 4: Top Targets + Activity Feed ──
    col_targets, col_activity = st.columns([1.4, 1])

    with col_targets:
        st.markdown("<div class='section-title'>🏆 Top Targets by Priority</div>", unsafe_allow_html=True)
        top_t = ov.get("top_targets", [])
        if top_t:
            for i, tgt in enumerate(top_t[:6]):
                pct = tgt.get("priority", 0)
                bar_w = min(max(pct, 5), 100)
                color = "#22c55e" if pct >= 70 else "#eab308" if pct >= 40 else "#6b7280"
                st.markdown(f"""
                <div style="margin-bottom:10px;">
                  <div style="display:flex;justify-content:space-between;font-size:13px;">
                    <span style="color:#e2e4e9;font-weight:500;">{tgt.get('name', '?')}</span>
                    <span style="color:#6b7280;">roi {tgt.get('roi_score', 0)} · {tgt.get('endpoint_count', 0)} eps</span>
                  </div>
                  <div style="background:#1a1e2a;border-radius:4px;height:6px;margin-top:4px;">
                    <div style="width:{bar_w}%;background:{color};height:6px;border-radius:4px;"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No targets yet.")

    with col_activity:
        st.markdown("<div class='section-title'>⚡ Recent Activity</div>", unsafe_allow_html=True)
        activity = _fetch_activity(backend_base) if use_backend else None
        if activity and activity.get("events"):
            type_colors = {"finding": "#8b5cf6", "verdict": "#f97316", "scan": "#3b82f6", "evidence": "#6b7280"}
            type_icons = {"finding": "🔍", "verdict": "⚖️", "scan": "📡", "evidence": "📄"}
            for ev in activity["events"][:12]:
                ev_type = ev.get("type", "unknown")
                color = type_colors.get(ev_type, "#6b7280")
                icon = type_icons.get(ev_type, "•")
                title = ev.get("title") or ev.get("status") or ev.get("mode") or ev.get("attempt") or ""
                ts = ev.get("timestamp", "")[:19] if ev.get("timestamp") else ""
                st.markdown(f"""
                <div class="activity-item">
                  <span class="activity-type-badge" style="background:{color}22;color:{color}">{icon} {ev_type}</span>
                  <span class="activity-detail">{title}</span>
                  <span class="activity-time">{ts}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No recent activity.")

    # ── Row 5: Quick Wins ──
    st.markdown("<div class='section-title'>⚡ Quick Wins — Monetization Opportunities</div>", unsafe_allow_html=True)
    qw_data = _fetch_quick_wins(backend_base) if use_backend else None
    if qw_data and qw_data.get("report"):
        report = qw_data["report"]
        col_qw1, col_qw2, col_qw3, col_qw4 = st.columns(4)
        with col_qw1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{report.get("total_opportunities", 0)}</div><div class="metric-label">Opportunities</div></div>', unsafe_allow_html=True)
        with col_qw2:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{report.get("avg_quick_win_score", 0):.2f}</div><div class="metric-label">Avg Score</div></div>', unsafe_allow_html=True)
        with col_qw3:
            st.markdown(f'<div class="metric-card"><div class="metric-value">${report.get("total_estimated_value", 0):,.0f}</div><div class="metric-label">Est. Value</div></div>', unsafe_allow_html=True)
        with col_qw4:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{report.get("fastest_path_minutes", 0)}min</div><div class="metric-label">Fastest Path</div></div>', unsafe_allow_html=True)

        top_wins = report.get("top_quick_wins", [])
        if top_wins:
            cat_icons = {"ready_to_report": "✅", "half_confirmed": "🔄", "low_hanging_fruit": "🍎", "underexplored": "🔍"}
            for w in top_wins[:5]:
                icon = cat_icons.get(w.get("category", ""), "•")
                st.markdown(f"""
                <div class="activity-item">
                  <span style="font-size:13px;font-weight:600;color:#22c55e;min-width:36px;">{w.get('quick_win_score', 0):.2f}</span>
                  <span class="activity-detail">
                    <span style="color:#e2e4e9;">{w.get('endpoint_method', 'GET')}</span>
                    <span style="color:#6b7280;">{w.get('endpoint_path', '/')}</span>
                    <span style="color:#6b7280;font-size:11px;"> — {icon} {w.get('category', '')}</span>
                  </span>
                  <span style="color:#6b7280;font-size:11px;white-space:nowrap;">
                    ${w.get('estimated_payout', 0):,.0f} · {w.get('estimated_effort_minutes', 0)}min
                  </span>
                </div>
                """, unsafe_allow_html=True)
            st.caption("Top quick wins ranked by speed-to-payout. Focus on ready_to_report and low_hanging_fruit first.")
        else:
            st.caption("No quick win opportunities. Run scans to generate data.")

        low_effort = report.get("low_effort_high_roi_targets", [])
        if low_effort:
            st.markdown("<div class='section-subtitle'>🎯 Low Effort, High ROI</div>", unsafe_allow_html=True)
            for le in low_effort[:3]:
                st.markdown(f"""
                <div style="padding:4px 0;font-size:12px;color:#6b7280;">
                  <span style="color:#e2e4e9;">{le.get('endpoint_method', 'GET')} {le.get('endpoint_path', '/')}</span>
                  ROI {le.get('roi_score', 0):.2f} · {le.get('effort_estimate_minutes', 0)}min
                  {" · ⚠️ partial" if le.get('is_partially_confirmed') else ""}
                  {" · 🔍 underexplored" if le.get('is_underexplored') else ""}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("Quick Wins engine requires API backend. Start the backend server to see opportunities.")

    # ── Row 6: High-Signal Endpoints + Intelligence ──
    col_signal, col_intel = st.columns([1.4, 1])

    with col_signal:
        st.markdown("<div class='section-title'>📡 High-Signal Endpoints</div>", unsafe_allow_html=True)
        digest = _fetch_digest(backend_base) if use_backend else None
        if digest and digest.get("high_signal"):
            for item in digest["high_signal"][:8]:
                rs = item.get("risk_score", 0)
                color = "#ef4444" if rs >= 50 else "#f97316" if rs >= 25 else "#eab308"
                labels = ", ".join(item.get("labels", [])[:3])
                st.markdown(f"""
                <div class="activity-item">
                  <span style="font-size:13px;font-weight:600;color:{color};min-width:40px;">{rs:.0f}</span>
                  <span class="activity-detail">
                    <span style="color:#e2e4e9;">{item.get('method','GET')}</span>
                    <span style="color:#6b7280;">{item.get('path','/')}</span>
                    {f'<span style="color:#6b7280;font-size:11px;">— {labels}</span>' if labels else ''}
                  </span>
                </div>
                """, unsafe_allow_html=True)
            st.caption(f"Showing top {min(len(digest['high_signal']), 8)} of {digest.get('total_endpoints', 0)} endpoints")
        else:
            st.caption("No high-signal endpoints. Run a scan to discover endpoints.")

    with col_intel:
        st.markdown("<div class='section-title'>🧠 Program Intelligence</div>", unsafe_allow_html=True)
        intel = _fetch_intel(backend_base) if use_backend else None
        if intel and intel.get("total_programs", 0) > 0:
            pi = intel
            st.markdown(f"""
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
              <span class="intel-chip">📊 {pi.get('total_programs', 0)} programs</span>
              <span class="intel-chip">⭐ Q {pi.get('avg_quality', 0)}</span>
              <span class="intel-chip">🧩 C {pi.get('avg_complexity', 0)}</span>
              <span class="intel-chip">💰 ROI {pi.get('avg_roi', 0)}</span>
              <span class="intel-chip">🆕 F {pi.get('avg_freshness', 0)}</span>
            </div>
            """, unsafe_allow_html=True)
            platforms = pi.get("platform_distribution", {})
            if platforms and pd:
                df_plat = pd.DataFrame(list(platforms.items()), columns=["Platform", "Count"])
                fig = px.bar(df_plat, x="Count", y="Platform", orientation="h", text="Count")
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#c4c8d4", "size": 10}, xaxis={"visible": False},
                    margin={"l": 10, "r": 10, "t": 5, "b": 5}, height=140, showlegend=False,
                )
                fig.update_traces(marker_color="#8b5cf6", textfont_color="#c4c8d4")
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            # Show default state with real data — no mock
            session = db.SessionLocal()
            try:
                target_count = session.query(models.Target).count()
                endpoint_count = session.query(models.Endpoint).count()
                finding_count = session.query(models.Finding).count()
            finally:
                session.close()
            st.markdown(f"""
            <div style="color:#6b7280;font-size:13px;padding:8px 0;">
              <div style="display:flex;flex-wrap:wrap;gap:8px;">
                <span class="intel-chip">🎯 {target_count} targets</span>
                <span class="intel-chip">🔗 {endpoint_count} endpoints</span>
                <span class="intel-chip">📋 {finding_count} findings</span>
              </div>
              <p style="margin-top:16px;">Add bug bounty program intel to see platform distribution and quality metrics.</p>
            </div>
            """, unsafe_allow_html=True)

    # ── Row 6: Attack Surface Summary ──
    st.markdown("<div class='section-title'>🗺️ Attack Surface</div>", unsafe_allow_html=True)
    col_as, col_next = st.columns([1.4, 1])

    with col_as:
        surfaces = _fetch_attack_surfaces(backend_base) if use_backend else None
        if surfaces:
            total_surface_eps = sum(len(v) for v in surfaces.values())
            st.markdown(f"<div class='section-subtitle'>{len(surfaces)} surface categories · {total_surface_eps} endpoints</div>", unsafe_allow_html=True)
            surf_items = sorted(surfaces.items(), key=lambda kv: sum(e.get("risk_score", 0) for e in kv[1]), reverse=True)
            for surface_name, eps in surf_items[:6]:
                actionable = sum(1 for e in eps if e.get("actionable"))
                total_eps = len(eps)
                avg_rs = round(sum(e.get("risk_score", 0) for e in eps) / max(total_eps, 1), 1)
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #1a1e2a;font-size:13px;">
                  <span style="color:#e2e4e9;">{surface_name}</span>
                  <span style="color:#6b7280;">{total_eps} eps · {actionable} actionable · avg risk {avg_rs}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Compute directly from engine
            session = db.SessionLocal()
            try:
                endpoints = session.query(models.Endpoint).all()
                if endpoints:
                    mapper = AttackSurfaceMapper()
                    noise = NoiseReductionLayer()
                    report = noise.reduce([{"path": e.path, "method": e.method, "params": e.parsed_params} for e in endpoints])
                    surface_map = mapper.map(endpoints)
                    if hasattr(surface_map, 'idor_clusters') and surface_map.idor_clusters:
                        st.markdown(f"**IDOR/BOLA clusters:** {len(surface_map.idor_clusters)}")
                    if hasattr(surface_map, 'auth_boundaries') and surface_map.auth_boundaries:
                        st.markdown(f"**Auth boundaries:** {len(surface_map.auth_boundaries)}")
                    if hasattr(surface_map, 'multi_tenant_zones') and surface_map.multi_tenant_zones:
                        st.markdown(f"**Multi-tenant zones:** {len(surface_map.multi_tenant_zones)}")
                    if hasattr(surface_map, 'graphql_surfaces') and surface_map.graphql_surfaces:
                        st.markdown(f"**GraphQL surfaces:** {len(surface_map.graphql_surfaces)}")
                    st.caption(f"Noise reduction: {getattr(report, 'noise_ratio', 0)*100:.0f}% noise ratio")
                else:
                    st.caption("No endpoints discovered yet. Run a scan to populate the attack surface.")
            finally:
                session.close()

    with col_next:
        st.markdown("<div class='section-title'>🎯 Suggested Actions</div>", unsafe_allow_html=True)
        session = db.SessionLocal()
        try:
            actionable_eps = session.query(models.Endpoint).limit(100).all()
            suggestions = []
            for ep in actionable_eps:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                if s.get("actionable") and s.get("risk_score", 0) >= 25:
                    sug = generate_suggestions(ep.path, ep.method or "GET", ep.parsed_params)
                    if sug:
                        suggestions.append({"path": f"{ep.method} {ep.path}", "suggestion": sug[0], "score": s["risk_score"]})
                    if len(suggestions) >= 5:
                        break
            if suggestions:
                for sug in suggestions:
                    st.markdown(f"""
                    <div style="padding:6px 0;border-bottom:1px solid #1a1e2a;font-size:13px;">
                      <div style="color:#e2e4e9;">{sug['path']}</div>
                      <div style="color:#6b7280;font-size:12px;">{sug['suggestion'][:120]}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No actionable endpoints found. Run scans to discover high-value paths.")
        finally:
            session.close()

    # ── AI Assistant Panel ──
    from dashboard.pages.ai_panel import render_ai_panel
    render_ai_panel(backend_base, use_backend)

    # ── System Health Footer ──
    health = _fetch_health(backend_base) if use_backend else None
    if health:
        db_stats = health.get("database", {})
        pipeline_h = health.get("pipeline", {})
        st.markdown(f"""
        <div style="margin-top:24px;padding:12px 16px;background:#13161e;border:1px solid #1e2230;border-radius:8px;">
          <div style="display:flex;justify-content:space-between;font-size:12px;color:#6b7280;">
            <span>🟢 System Healthy</span>
            <span>DB: {db_stats.get('targets', 0)}T · {db_stats.get('endpoints', 0)}E · {db_stats.get('findings', 0)}F · {db_stats.get('verdicts', 0)}V</span>
            <span>Pipeline: {pipeline_h.get('confirmed_verdicts', 0)} confirmed · {pipeline_h.get('active_scans', 0)} active scans</span>
          </div>
        </div>
        """, unsafe_allow_html=True)


def _compute_overview_local() -> Optional[Dict[str, Any]]:
    """Fallback when API is unavailable — compute overview from DB directly."""
    session = db.SessionLocal()
    try:
        targets = session.query(models.Target).all()
        endpoints = session.query(models.Endpoint).all()
        findings = session.query(models.Finding).all()
        verdicts = session.query(models.Verdict).all()
        scan_runs = session.query(models.ScanRun).all()

        target_count = len(targets)
        endpoint_count = len(endpoints)
        finding_count = len(findings)
        active_scans = sum(1 for s in scan_runs if s.status in ("pending", "running"))
        confirmed_verdicts = sum(1 for v in verdicts if v.status == "confirmed")

        high_signal = 0
        total_risk = 0.0
        risk_buckets: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        vector_dist: Dict[str, int] = {}

        for ep in endpoints:
            s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
            rs = s.get("risk_score", 0)
            total_risk += rs
            if rs >= 50:
                risk_buckets["critical"] += 1
                high_signal += 1
            elif rs >= 25:
                risk_buckets["high"] += 1
                high_signal += 1
            elif rs >= 10:
                risk_buckets["medium"] += 1
            elif rs >= 1:
                risk_buckets["low"] += 1
            else:
                risk_buckets["info"] += 1
            vec = s.get("vector", "Unknown")
            vector_dist[vec] = vector_dist.get(vec, 0) + 1

        avg_risk = round(total_risk / max(endpoint_count, 1), 1)

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            sev = (f.severity or "info").lower()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        pipeline_stages = {"detected": 0, "validated": 0, "confirmed": 0, "reported": 0}
        endpoint_verdicts: Dict[int, List] = {}
        for v in verdicts:
            if v.endpoint_id:
                endpoint_verdicts.setdefault(v.endpoint_id, []).append(v)
        for f in findings:
            ep_verdicts = endpoint_verdicts.get(f.endpoint_id or 0, [])
            if any(v.status == "confirmed" for v in ep_verdicts):
                pipeline_stages["confirmed"] += 1
                pipeline_stages["reported"] += 1
            elif ep_verdicts:
                pipeline_stages["validated"] += 1
            else:
                pipeline_stages["detected"] += 1

        return {
            "target_count": target_count,
            "endpoint_count": endpoint_count,
            "finding_count": finding_count,
            "confirmed_verdicts": confirmed_verdicts,
            "active_scans": active_scans,
            "high_signal_endpoints": high_signal,
            "avg_risk_score": avg_risk,
            "risk_distribution": risk_buckets,
            "vector_distribution": vector_dist,
            "severity_counts": severity_counts,
            "pipeline_stages": pipeline_stages,
            "top_targets": [],
        }
    finally:
        session.close()
