"""
AI Assistant panel — embedded chat, insights, recommendations for Mission Control.
"""

from __future__ import annotations

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


def _api_get(url: str) -> Optional[Any]:
    if not http_requests:
        return None
    try:
        r = http_requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _api_post(url: str, payload: dict) -> Optional[Dict[str, Any]]:
    if not http_requests:
        return None
    try:
        r = http_requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _severity_color(s: str) -> str:
    return {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#3b82f6", "info": "#6b7280"}.get(s.lower(), "#6b7280")


def _insights_count(backend_base: str, use_backend: bool) -> int:
    data = _api_get(f"{backend_base}/api/assistant/insights") if use_backend else None
    return len(data) if data else 0


AI_PANEL_CSS = """
<style>
.ai-panel-toggle {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px; margin: 16px 0 0 0;
  background: linear-gradient(135deg, #7c3aed15, #a855f708);
  border: 1px solid #7c3aed40; border-radius: 10px;
  cursor: pointer; transition: all 0.15s;
  font-size: 14px; font-weight: 600; color: #c084fc;
}
.ai-panel-toggle:hover { border-color: #a855f7; background: #7c3aed20; }
.ai-panel-toggle .badge {
  background: #7c3aed40; color: #c084fc; font-size: 9px; font-weight: 700;
  padding: 2px 7px; border-radius: 10px; margin-left: auto;
}

.ai-section {
  background: #13161e; border: 1px solid #1e2230;
  border-radius: 10px; padding: 16px; margin-bottom: 12px;
}
.ai-section-title {
  font-size: 12px; font-weight: 700; color: #e2e4e9;
  margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
}
.ai-section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}

.ai-insight-card {
  padding: 10px 12px; margin-bottom: 6px;
  background: #0d0f14; border-left: 3px solid #7c3aed;
  border-radius: 0 6px 6px 0; cursor: pointer;
  transition: background 0.12s;
}
.ai-insight-card:hover { background: #1a1e2a; }
.ai-insight-card .type {
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.6px; margin-bottom: 2px;
}
.ai-insight-card .title {
  font-size: 12px; font-weight: 600; color: #e2e4e9;
}
.ai-insight-card .detail {
  font-size: 11px; color: #6b7280; margin-top: 2px;
}
.ai-insight-card .action {
  font-size: 10px; color: #a855f7; margin-top: 4px;
}

.ai-rec-card {
  padding: 10px 12px; margin-bottom: 6px;
  background: #0d0f14; border-radius: 6px;
  transition: background 0.12s;
}
.ai-rec-card:hover { background: #1a1e2a; }
.ai-rec-card .target {
  font-size: 13px; font-weight: 600; color: #e2e4e9;
}
.ai-rec-card .meta {
  font-size: 11px; color: #6b7280; margin-top: 2px;
}
.ai-rec-card .stats {
  display: flex; gap: 12px; margin-top: 6px; flex-wrap: wrap;
}
.ai-rec-card .stat {
  font-size: 10px; font-weight: 600;
}
.ai-rec-card .stat.roi { color: #22c55e; }
.ai-rec-card .stat.priority { color: #a855f7; }
.ai-rec-card .stat.time { color: #f97316; }
.ai-rec-card .stat.payout { color: #fbbf24; }
.ai-rec-card .stat.critical { color: #ef4444; }
.ai-rec-card .stat.idor { color: #a855f7; }

.ai-chat-messages {
  background: #0d0f14; border-radius: 8px; padding: 12px;
  min-height: 240px; max-height: 400px; overflow-y: auto;
  margin-bottom: 10px;
}
.ai-msg {
  margin-bottom: 10px; animation: fadeIn 0.2s ease;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
.ai-msg.user { text-align: right; }
.ai-msg .bubble {
  display: inline-block; max-width: 85%; text-align: left;
  padding: 8px 12px; border-radius: 10px;
  font-size: 12px; line-height: 1.5;
}
.ai-msg.user .bubble {
  background: #7c3aed; color: #fff;
  border-bottom-right-radius: 2px;
}
.ai-msg.assistant .bubble {
  background: #1e2230; color: #c4c8d4;
  border-bottom-left-radius: 2px;
}
.ai-msg .source-tag {
  font-size: 9px; color: #6b7280; margin-top: 3px;
  display: inline-block;
}

.ai-quick-actions {
  display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap;
}
.ai-quick-actions .stButton > button {
  background: #1e2230 !important; border: 1px solid #2a2f42 !important;
  color: #c4c8d4 !important; border-radius: 6px !important;
  font-size: 11px !important; font-weight: 500 !important;
  padding: 4px 12px !important;
}
.ai-quick-actions .stButton > button:hover {
  border-color: #7c3aed80 !important; color: #c084fc !important;
}

.ai-controls {
  display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
  font-size: 12px; color: #6b7280;
}
.ai-controls .stCheckbox { margin: 0; }
.ai-controls .stButton > button {
  background: #1e2230 !important; border: 1px solid #2a2f42 !important;
  color: #c4c8d4 !important; border-radius: 6px !important;
  font-size: 11px !important; font-weight: 500 !important;
  padding: 2px 14px !important; height: 28px !important;
}
.ai-controls .stButton > button:hover {
  border-color: #7c3aed80 !important;
}
.ai-controls .refresh-time {
  font-size: 10px; color: #525668;
}

.ai-provider-badge {
  font-size: 10px; color: #6b7280; text-align: right; margin-top: 8px;
}
</style>
"""

QUICK_ACTIONS = [
    {"label": "🎯 ROI", "query": "¿Qué target tiene mejor ROI?"},
    {"label": "🆕 Cambios", "query": "¿Qué cambió hoy?"},
    {"label": "⚡ Quick Wins", "query": "¿Qué oportunidades puedo completar en dos horas?"},
    {"label": "📡 Escaneos", "query": "¿Hay escaneos activos?"},
    {"label": "📋 Reportes", "query": "¿Qué reporte está casi listo?"},
]


AUTO_REFRESH_INTERVAL = 30


def render_ai_panel(backend_base: str, use_backend: bool):
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []
    if "ai_expanded" not in st.session_state:
        st.session_state.ai_expanded = False

    st.markdown(AI_PANEL_CSS, unsafe_allow_html=True)

    # ── Toggle ──
    badge = ""
    if not st.session_state.ai_expanded:
        count = _insights_count(backend_base, use_backend)
        badge = f" · {count} insights" if count else ""

    indicator = "▲" if st.session_state.ai_expanded else "▼"
    if st.button(f"🤖 AI Assistant  {indicator}{badge}", key="ai_toggle", use_container_width=True):
        st.session_state.ai_expanded = not st.session_state.ai_expanded
        st.rerun()

    if not st.session_state.ai_expanded:
        return

    # ── Controls bar ──
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        auto_on = st.checkbox(
            "Auto-refresh",
            value=st.session_state.get("ai_auto_refresh", False),
            key="ai_auto_refresh",
            help=f"Refresh insights every {AUTO_REFRESH_INTERVAL}s",
        )
    with c2:
        if "ai_last_refresh" not in st.session_state:
            st.session_state.ai_last_refresh = datetime.now().strftime("%H:%M:%S")
        st.markdown(
            f'<div class="refresh-time" style="padding-top:6px;">🔄 {st.session_state.ai_last_refresh}</div>',
            unsafe_allow_html=True,
        )
    with c3:
        if st.button("Refresh now", key="ai_refresh_btn"):
            st.session_state.ai_last_refresh = datetime.now().strftime("%H:%M:%S")
            st.rerun()

    # ── Left + Right columns ──
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        _render_data_section(backend_base, use_backend, auto_on)

    with col_right:
        _render_chat_section(backend_base, use_backend)

    # ── Provider footer ──
    status_data = _api_get(f"{backend_base}/api/assistant/status") if use_backend else None
    if status_data:
        prov = status_data.get("provider", "?")
        avail = status_data.get("available", False)
        st.markdown(
            f'<div class="ai-provider-badge">Provider: {prov} · {"🟢 Available" if avail else "🔴 Unavailable"}</div>',
            unsafe_allow_html=True,
        )


@st.fragment(run_every=AUTO_REFRESH_INTERVAL)
def _render_data_section(backend_base: str, use_backend: bool, auto_on: bool):
    """Fragment that auto-refreshes insights + recommendations when auto_on is set."""
    if auto_on:
        st.session_state.ai_last_refresh = datetime.now().strftime("%H:%M:%S")

    _render_insights(backend_base, use_backend)
    _render_recommendations(backend_base, use_backend)


def _render_insights(backend_base: str, use_backend: bool):
    st.markdown('<div class="ai-section">', unsafe_allow_html=True)

    insights: List[Dict] = []
    if use_backend:
        data = _api_get(f"{backend_base}/api/assistant/insights")
        if data:
            insights = data[:6]

    count = len(insights)
    st.markdown(
        f'<div class="ai-section-title">⚡ Insights <span style="color:#6b7280;font-weight:400;font-size:11px;">({count})</span></div>',
        unsafe_allow_html=True,
    )

    if not insights:
        st.caption("No insights available. Run scans to generate data.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    for ins in insights:
        sev = ins.get("severity", "info")
        color = _severity_color(sev)
        title = ins.get("title", "")
        detail = ins.get("detail", "")
        action = ins.get("action", "")
        st.markdown(f"""
        <div class="ai-insight-card" style="border-left-color:{color};">
          <div class="type" style="color:{color};">{sev} · {ins.get('type', '')}</div>
          <div class="title">{title}</div>
          <div class="detail">{detail}</div>
          {f'<div class="action">→ {action}</div>' if action else ''}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_recommendations(backend_base: str, use_backend: bool):
    st.markdown('<div class="ai-section">', unsafe_allow_html=True)

    recs: List[Dict] = []
    if use_backend:
        data = _api_get(f"{backend_base}/api/assistant/recommendations")
        if data:
            recs = data[:4]

    count = len(recs)
    st.markdown(
        f'<div class="ai-section-title">🎯 Recommendations <span style="color:#6b7280;font-weight:400;font-size:11px;">({count})</span></div>',
        unsafe_allow_html=True,
    )

    if not recs:
        st.caption("No recommendations yet. Add more targets.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    for rec in recs:
        target = rec.get("target_name", "?")
        domain = rec.get("domain", "")
        roi = rec.get("roi_score", 0)
        priority = rec.get("priority_score", 0)
        time_min = rec.get("estimated_time_minutes", 0)
        payout = rec.get("estimated_payout", 0)
        critical = rec.get("critical_endpoints", 0)
        idor = rec.get("idor_candidates", 0)
        reason = rec.get("reason", "")

        hours = time_min // 60
        mins = time_min % 60
        time_str = f"{hours}h {mins}m" if hours else f"{mins}m"

        st.markdown(f"""
        <div class="ai-rec-card">
          <div class="target">{target} <span style="color:#6b7280;font-weight:400;">{domain}</span></div>
          <div class="meta">{reason}</div>
          <div class="stats">
            <span class="stat roi">ROI {roi}</span>
            <span class="stat priority">P {priority:.0f}</span>
            <span class="stat time">{time_str}</span>
            <span class="stat payout">${payout:,}</span>
            <span class="stat critical">{critical} crit</span>
            {f'<span class="stat idor">{idor} IDOR</span>' if idor else ''}
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_chat_section(backend_base: str, use_backend: bool):
    st.markdown('<div class="ai-section">', unsafe_allow_html=True)
    st.markdown('<div class="ai-section-title">💬 Chat</div>', unsafe_allow_html=True)

    messages_html = '<div class="ai-chat-messages">'
    if st.session_state.ai_messages:
        for msg in st.session_state.ai_messages:
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            source = msg.get("source", "")
            messages_html += f'<div class="ai-msg {role}"><div class="bubble">{content}</div>'
            if source and role == "assistant":
                messages_html += f'<div class="source-tag">source: {source}</div>'
            messages_html += "</div>"
    else:
        messages_html += '<div style="color:#6b7280;font-size:12px;padding:20px 0;text-align:center;">Ask me anything about your targets, findings, or recommendations.</div>'
    messages_html += "</div>"
    st.markdown(messages_html, unsafe_allow_html=True)

    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        user_input = st.text_input(
            "Ask the assistant...",
            key="ai_chat_input",
            label_visibility="collapsed",
            placeholder="Ej: ¿Qué target tiene mejor ROI?",
        )
    with col_btn:
        send = st.button("Send", key="ai_send", use_container_width=True)

    if send and user_input and use_backend:
        st.session_state.ai_messages.append({"role": "user", "content": user_input})
        result = _api_post(f"{backend_base}/api/assistant/chat", {"message": user_input})
        if result:
            answer = result.get("answer", "No response")
            source = result.get("source", "")
            st.session_state.ai_messages.append({"role": "assistant", "content": answer, "source": source})
        else:
            st.session_state.ai_messages.append({"role": "assistant", "content": "Assistant unavailable. Check backend connection.", "source": ""})
        st.rerun()

    if st.session_state.ai_messages:
        if st.button("Clear chat", key="ai_clear", use_container_width=True):
            st.session_state.ai_messages = []
            st.rerun()

    st.markdown("<div class='ai-quick-actions'>", unsafe_allow_html=True)
    for qa in QUICK_ACTIONS:
        if st.button(qa["label"], key=f"qa_{qa['label']}", use_container_width=True):
            st.session_state.ai_messages.append({"role": "user", "content": qa["query"]})
            if use_backend:
                result = _api_post(f"{backend_base}/api/assistant/chat", {"message": qa["query"]})
                if result:
                    answer = result.get("answer", "No response")
                    source = result.get("source", "")
                    st.session_state.ai_messages.append({"role": "assistant", "content": answer, "source": source})
                else:
                    st.session_state.ai_messages.append({"role": "assistant", "content": "Assistant unavailable.", "source": ""})
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
