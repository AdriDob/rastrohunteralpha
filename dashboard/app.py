import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st

try:
    import requests as http_requests
except ImportError:
    http_requests = None
    import urllib.request as urlrequest
    import urllib.error as urlerror

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.engine.unified_scoring import score as unified_score, score_target as unified_score_target, generate_suggestions
from core.targets.models import TargetIntel
from database import db, models

st.set_page_config(page_title="Rastro", layout="wide", initial_sidebar_state="expanded")

try:
    db.init_db()
except Exception:
    pass

BACKEND_BASE = os.environ.get("RASTRO_BACKEND", "http://127.0.0.1:8000")

if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "editor_mode" not in st.session_state:
    st.session_state.editor_mode = False

# ── Custom CSS ─────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  /* ── Reset Streamlit chrome ── */
  #root > div:first-child > div:first-child > div:first-child > div:first-child { padding-top: 0 !important; }
  .stApp > header { display: none !important; }
  [data-testid="stHeader"] { display: none !important; }
  [data-testid="stToolbar"] { display: none !important; }
  [data-testid="stDecoration"] { display: none !important; }
  .stDeployButton { display: none !important; }
  #MainMenu { display: none !important; }
  footer { display: none !important; }
  .stActionButton { display: none !important; }

  /* ── Base ── */
  html, body, [data-testid="stAppViewContainer"] {
    background-color: #0d0f14 !important;
    color: #e2e4e9 !important;
    font-family: 'Inter', -apple-system, sans-serif;
  }
  [data-testid="stAppViewContainer"] > .main { background-color: #0d0f14 !important; }
  .main .block-container { padding: 0 24px 24px 24px !important; max-width: 100% !important; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0d0f14; }
  ::-webkit-scrollbar-thumb { background: #1e2230; border-radius: 3px; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background-color: #0d0f14 !important;
    border-right: 1px solid #1e2230 !important;
    min-width: 220px !important;
    max-width: 220px !important;
    width: 220px !important;
    padding-top: 0 !important;
  }
  section[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
  section[data-testid="stSidebar"] > div:first-child > div:first-child { padding: 0 !important; }
  .st-emotion-cache-1wsx8qw, .st-emotion-cache-6qob1r { display: none !important; }

  .sidebar-logo {
    display: flex; align-items: center; gap: 12px;
    padding: 24px 20px 20px 20px;
    border-bottom: 1px solid #1e2230;
  }
  .sidebar-collapse {
    margin-left: auto; color: rgba(255,255,255,0.2); cursor: pointer;
    font-size: 14px; transition: color 0.15s;
  }
  .sidebar-collapse:hover { color: rgba(255,255,255,0.5); }
  .logo-icon {
    width: 34px; height: 34px; border-radius: 10px;
    background: linear-gradient(135deg, #7c3aed, #a855f7);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 800; font-size: 15px; letter-spacing: 0;
  }
  .logo-text {
    color: #fff; font-weight: 800; font-size: 18px; letter-spacing: 2.5px;
  }

  .nav-section { padding: 14px 8px 2px 8px; }
  .nav-section-label {
    color: rgba(255,255,255,0.25); font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 6px; padding: 0 8px;
  }
  .nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 7px 12px; margin: 1px 0;
    border-radius: 6px; cursor: pointer;
    color: rgba(255,255,255,0.5); font-size: 13px; font-weight: 500;
    text-decoration: none; transition: all 0.15s;
    position: relative;
  }
  .nav-item:hover { background: rgba(124,58,237,0.08); color: #e2e4e9; }
  .nav-item.active {
    background: #7c3aed1a; color: #fff; font-weight: 600;
    border-left: 2px solid #7c3aed; border-radius: 0 6px 6px 0;
  }
  .nav-item-icon { width: 18px; text-align: center; font-size: 14px; }

  .sidebar-status {
    padding: 16px 20px;
    border-top: 1px solid #1e2230;
    margin-top: 8px;
  }
  .sidebar-status-label {
    color: rgba(255,255,255,0.25); font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 8px;
  }
  .sidebar-status-dot {
    display: inline-block; width: 7px; height: 7px; border-radius: 50%;
    background: #22c55e; margin-right: 7px;
    box-shadow: 0 0 8px rgba(34,197,94,0.5);
  }
  .sidebar-status-text { color: rgba(255,255,255,0.6); font-size: 12px; display: flex; align-items: center; }

  /* ── Sidebar Streamlit overrides ── */
  section[data-testid="stSidebar"] .stCheckbox { margin: 0 16px; }
  section[data-testid="stSidebar"] .stCheckbox label { color: rgba(255,255,255,0.4) !important; font-size: 12px !important; }
  section[data-testid="stSidebar"] hr { margin: 8px 16px; border-color: #1e2230 !important; }
  section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important; border: none !important;
    padding: 7px 12px !important; margin: 1px 0 !important;
    border-radius: 6px !important; color: rgba(255,255,255,0.5) !important;
    font-size: 13px !important; font-weight: 500 !important; font-family: 'Inter', sans-serif !important;
    justify-content: flex-start !important; text-align: left !important;
    transition: all 0.15s; width: 100% !important;
  }
  section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(124,58,237,0.08) !important; color: #e2e4e9 !important; border: none !important;
  }
  section[data-testid="stSidebar"] .stButton > button:active, section[data-testid="stSidebar"] .stButton > button:focus {
    border: none !important; box-shadow: none !important;
  }
  section[data-testid="stSidebar"] .stButton > button p { font-size: 13px !important; font-weight: 500 !important; }

  /* ── Header ── */
  .header-bar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 20px 0 16px 0;
    margin-bottom: 20px;
  }
  .header-left h1 {
    font-size: 26px !important; font-weight: 700 !important;
    color: #fff !important; margin: 0 0 2px 0 !important; padding: 0 !important;
    letter-spacing: -0.3px;
  }
  .header-left p { color: rgba(255,255,255,0.35); font-size: 13px; margin: 0; }
  .header-right { display: flex; align-items: center; gap: 14px; }
  .header-select {
    background: #13161e; border: 1px solid #1e2230; border-radius: 8px;
    padding: 7px 14px; color: #e2e4e9; font-size: 12px; font-weight: 500;
    cursor: pointer;
  }
  .header-icon-btn {
    width: 34px; height: 34px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: rgba(255,255,255,0.4); cursor: pointer; font-size: 16px;
    background: #13161e; border: 1px solid #1e2230;
    transition: all 0.15s;
  }
  .header-icon-btn:hover { color: #e2e4e9; border-color: rgba(255,255,255,0.15); }
  .header-avatar {
    width: 34px; height: 34px; border-radius: 8px;
    background: linear-gradient(135deg, #7c3aed, #a855f7);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 13px; font-weight: 700; cursor: pointer;
  }

  /* ── Stat Cards ── */
  .stat-card {
    background: #13161e; border: 1px solid #1e2230; border-radius: 12px;
    padding: 18px; height: 100%;
    transition: border-color 0.2s;
  }
  .stat-card:hover { border-color: #7c3aed40; box-shadow: 0 0 20px rgba(124,58,237,0.06); }
  .stat-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .stat-card-icon {
    width: 38px; height: 38px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px;
  }
  .stat-card-badge {
    font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 20px;
    background: rgba(34,197,94,0.12); color: #4ade80;
  }
  .stat-card-label { color: rgba(255,255,255,0.4); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 2px; }
  .stat-card-value { color: #fff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px; line-height: 1.1; }
  .stat-card-trend { font-size: 11px; font-weight: 600; margin-top: 6px; }
  .stat-card-trend.up { color: #4ade80; }
  .stat-card-trend.down { color: #f87171; }

  /* ── Section Header ── */
  .section-header {
    display: flex; justify-content: space-between; align-items: center;
    margin: 28px 0 16px 0;
  }
  .section-header-left h2 {
    font-size: 18px !important; font-weight: 700 !important;
    color: #fff !important; margin: 0 0 2px 0 !important; letter-spacing: -0.2px !important;
  }
  .section-header-left p { color: rgba(255,255,255,0.35); font-size: 12px; margin: 0; }
  .section-header-right { display: flex; align-items: center; gap: 8px; }
  .btn-ghost {
    background: transparent; border: 1px solid #1e2230; border-radius: 8px;
    color: rgba(255,255,255,0.6); padding: 6px 14px; font-size: 12px; font-weight: 500;
    cursor: pointer; transition: all 0.15s;
  }
  .btn-ghost:hover { border-color: rgba(255,255,255,0.12); color: #e2e4e9; }
  .btn-primary {
    background: #7c3aed; border: 1px solid #7c3aed; border-radius: 8px;
    color: #fff; padding: 6px 16px; font-size: 12px; font-weight: 600;
    cursor: pointer; transition: all 0.2s;
  }
  .btn-primary:hover { background: #6d28d9; border-color: #6d28d9; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(124,58,237,0.35); }

  /* ── Data Table ── */
  .table-wrap {
    background: #13161e; border: 1px solid #1e2230; border-radius: 12px;
    overflow: hidden;
  }
  .data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .data-table thead th {
    text-align: left; padding: 12px 16px;
    color: rgba(255,255,255,0.3); font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.8px;
    border-bottom: 1px solid #1e2230;
    white-space: nowrap; background: #0d0f14;
  }
  .data-table tbody td {
    padding: 14px 16px;
    border-bottom: 1px solid #1e2230;
    color: #e2e4e9; vertical-align: middle;
  }
  .data-table tbody tr:last-child td { border-bottom: none; }
  .data-table tbody tr:hover { background: rgba(124,58,237,0.06); }
  .table-avatar {
    width: 30px; height: 30px; border-radius: 8px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; margin-right: 10px;
    vertical-align: middle; flex-shrink: 0;
  }
  .table-name { font-weight: 600; color: #fff; }
  .table-url { color: rgba(255,255,255,0.3); font-size: 11px; margin-top: 1px; }
  .table-progress-wrap { display: flex; align-items: center; gap: 8px; }
  .table-progress { flex: 1; height: 4px; background: #1e2230; border-radius: 4px; overflow: hidden; }
  .table-progress-bar { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #22c55e, #16a34a); }
  .badge-pill { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .badge-low { background: #16a34a20; color: #4ade80; }
  .badge-medium { background: #d9770620; color: #fbbf24; }
  .badge-high { background: #dc262620; color: #f87171; }
  .surface-tag {
    display: inline-block; padding: 2px 8px; background: rgba(255,255,255,0.04);
    border-radius: 4px; font-size: 11px; color: rgba(255,255,255,0.5); margin: 1px 2px;
  }
  .priority-critical { color: #f87171; font-weight: 700; font-size: 12px; }
  .priority-high { color: #fb923c; font-weight: 700; font-size: 12px; }
  .priority-medium { color: rgba(255,255,255,0.4); font-weight: 700; font-size: 12px; }
  .table-chevron { color: rgba(255,255,255,0.2); font-size: 18px; }

  /* ── Panels ── */
  .panel-card {
    background: #13161e; border: 1px solid #1e2230; border-radius: 12px;
    padding: 20px; height: 100%;
  }
  .panel-card h3 {
    font-size: 14px !important; font-weight: 700 !important;
    color: #fff !important; margin: 0 0 16px 0 !important;
  }

  /* ── Right panel ── */
  .right-panel-section {
    background: #13161e; border: 1px solid #1e2230; border-radius: 12px;
    padding: 20px; margin-bottom: 16px;
  }
  .right-panel-section h3 {
    font-size: 13px !important; font-weight: 700 !important;
    color: #fff !important; margin: 0 0 14px 0 !important;
  }
  .insight-card { position: relative; overflow: hidden; }
  .insight-gradient {
    position: absolute; top: -30px; right: -30px;
    width: 120px; height: 120px;
    background: radial-gradient(circle, rgba(124,58,237,0.25) 0%, transparent 70%);
    border-radius: 50%; pointer-events: none;
  }
  .insight-label {
    color: #a855f7; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 6px;
  }
  .insight-text { color: rgba(255,255,255,0.7); font-size: 13px; line-height: 1.6; margin-bottom: 14px; }

  .activity-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 10px 0; border-bottom: 1px solid #1e2230;
  }
  .activity-item:last-child { border-bottom: none; }
  .activity-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }
  .activity-text { font-size: 12px; color: #e2e4e9; line-height: 1.4; }
  .activity-subtext { font-size: 11px; color: rgba(255,255,255,0.3); margin-top: 2px; }
  .activity-ts { font-size: 11px; color: rgba(255,255,255,0.2); white-space: nowrap; }

  .view-all {
    color: #a855f7; font-size: 12px; font-weight: 600;
    text-decoration: none; cursor: pointer; display: inline-block; margin-top: 10px;
    transition: color 0.15s;
  }
  .view-all:hover { color: #c084fc; }

  /* ── Heatmap ── */
  .heatmap-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .heatmap-tile {
    border-radius: 8px; padding: 10px 8px; text-align: center;
  }
  .heatmap-tile-label { font-size: 10px; font-weight: 600; }
  .heatmap-tile-count { font-size: 20px; font-weight: 800; }

  /* ── Status Bar ── */
  .status-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 20px; margin-top: 24px;
    background: #13161e; border: 1px solid #1e2230; border-radius: 10px;
    font-size: 12px; color: #e2e4e9; flex-wrap: wrap; gap: 8px;
  }
  .status-bar-left { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
  .status-bar-right { display: flex; align-items: center; gap: 16px; }
  .status-item { display: flex; align-items: center; gap: 6px; }
  .status-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,0.5); }
  .status-live { color: #4ade80; font-size: 10px; font-weight: 700; }
  .status-label { color: rgba(255,255,255,0.35); }
  .status-value { color: #e2e4e9; font-weight: 600; }
  .status-refresh { cursor: pointer; color: #7c3aed; font-size: 16px; transition: transform 0.3s; }
  .status-refresh:hover { transform: rotate(180deg); color: #a855f7; }

  /* ── Legend ── */
  .legend-row { display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 12px; }
  .legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .legend-label { color: rgba(255,255,255,0.7); flex: 1; }
  .legend-count { color: #fff; font-weight: 600; }
  .legend-pct { color: rgba(255,255,255,0.3); }

  .donut-container { position: relative; width: 100%; max-width: 180px; margin: 0 auto; }
  .donut-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
  .donut-center-value { color: #fff; font-size: 20px; font-weight: 800; }
  .donut-center-label { color: rgba(255,255,255,0.3); font-size: 10px; }

  .hbar-row { display: flex; align-items: center; gap: 10px; margin: 5px 0; }
  .hbar-label { width: 80px; font-size: 12px; color: #e2e4e9; flex-shrink: 0; font-weight: 500; }
  .hbar-track { flex: 1; height: 16px; background: rgba(255,255,255,0.04); border-radius: 4px; overflow: hidden; }
  .hbar-bar { height: 100%; border-radius: 4px; transition: width 0.3s; }
  .hbar-stats { font-size: 11px; color: rgba(255,255,255,0.35); width: 70px; text-align: right; flex-shrink: 0; }

  .detection-item { padding: 6px 0; border-bottom: 1px solid #1e2230; font-size: 12px; }
  .detection-item:last-child { border-bottom: none; }
  .detection-path { color: #e2e4e9; word-break: break-all; }
  .detection-tags { display: flex; gap: 4px; margin-top: 3px; flex-wrap: wrap; }
  .detection-tag { padding: 1px 7px; border-radius: 3px; font-size: 10px; font-weight: 700; }
  .detection-tag.idor { background: rgba(124,58,237,0.15); color: #a855f7; }
  .detection-tag.graphql { background: rgba(34,197,94,0.15); color: #4ade80; }
  .detection-tag.export { background: rgba(249,115,22,0.15); color: #fb923c; }
  .detection-tag.high { background: rgba(239,68,68,0.15); color: #f87171; }
  .detection-tag.medium { background: rgba(245,158,11,0.15); color: #fbbf24; }
  .detection-ts { color: rgba(255,255,255,0.2); font-size: 11px; margin-top: 2px; }

  /* ── Tab overrides ── */
  .stTabs { background: transparent !important; border: none !important; }
  .stTabs [data-baseweb="tab-list"] {
    background: transparent !important; border-bottom: 1px solid #1e2230 !important;
    gap: 0 !important; padding: 0 !important;
  }
  .stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.3) !important;
    font-size: 12px !important; font-weight: 600 !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.15s;
  }
  .stTabs [data-baseweb="tab"]:hover { color: rgba(255,255,255,0.6) !important; }
  .stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #a855f7 !important;
    border-bottom: 2px solid #7c3aed !important;
  }
  .stTabs [data-baseweb="tab-panel"] { padding: 20px 0 !important; }

  .stMetric { background: #13161e !important; border: 1px solid #1e2230 !important; border-radius: 12px !important; padding: 16px !important; }
  .stMetric label { color: rgba(255,255,255,0.4) !important; font-size: 11px !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.6px !important; }
  .stMetric [data-testid="stMetricValue"] { color: #fff !important; font-size: 28px !important; font-weight: 700 !important; }
  div[data-testid="stMetricDelta"] { color: #4ade80 !important; font-size: 12px !important; font-weight: 600 !important; }

  .stRadio > div { background: #13161e !important; border: 1px solid #1e2230 !important; border-radius: 8px !important; padding: 4px !important; }
  .stRadio label { color: rgba(255,255,255,0.5) !important; font-size: 12px !important; }
  .stRadio label[data-selected="true"] { background: #7c3aed !important; color: #fff !important; border-radius: 6px !important; }
  .stSelectbox > div > div { background: #13161e !important; border: 1px solid #1e2230 !important; border-radius: 8px !important; color: #e2e4e9 !important; }
  .stTextInput > div > input { background: #13161e !important; border: 1px solid #1e2230 !important; border-radius: 8px !important; color: #e2e4e9 !important; }
  .stExpander { border: 1px solid #1e2230 !important; border-radius: 10px !important; background: #13161e !important; }
  .stExpander summary { color: #e2e4e9 !important; }
  .stButton > button { background: #13161e !important; border: 1px solid #1e2230 !important; color: #e2e4e9 !important; border-radius: 8px !important; font-size: 12px !important; font-weight: 500 !important; }
  .stButton > button:hover { border-color: #7c3aed80 !important; }
  .stCodeBlock { background: #0d0f14 !important; border: 1px solid #1e2230 !important; }
  .stCodeBlock pre { color: #e2e4e9 !important; }
  .dark-tab-content h1, .dark-tab-content h2, .dark-tab-content h3 { color: #fff !important; }
  hr { border-color: #1e2230 !important; }
  .stInfo, .stWarning, .stSuccess, .stError { background: #13161e !important; border: 1px solid #1e2230 !important; }
</style>
""", unsafe_allow_html=True)

# ── Helper functions ──────────────────────────────
def backend_get(path: str) -> dict | None:
    if not use_backend:
        return None
    url = BACKEND_BASE.rstrip("/") + path
    try:
        if http_requests:
            r = http_requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        req = urlrequest.Request(url)
        with urlrequest.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        st.warning(f"Backend error: {exc}")
        return None

def safe_fetch(path: str, label: str = "Loading"):
    """Fetch from backend with a spinning indicator."""
    with st.spinner(f"{label}..."):
        return backend_get(path)

def backend_post(path: str, payload: dict) -> dict | None:
    if not use_backend:
        return None
    url = BACKEND_BASE.rstrip("/") + path
    try:
        if http_requests:
            r = http_requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            return r.json()
        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlrequest.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        st.warning(f"Backend error: {exc}")
        return None

def get_session():
    return db.SessionLocal()

def score_color(s: float) -> str:
    if s >= 70: return "red"
    if s >= 40: return "orange"
    return "green"

# ── Sidebar ───────────────────────────────────────
with st.sidebar:
    use_backend = st.checkbox("Backend", value=True, label_visibility="collapsed", key="use_backend_toggle")

    st.markdown("""
    <div class="sidebar-logo">
      <div class="logo-icon">R</div>
      <span class="logo-text">RASTRO</span>
      <span class="sidebar-collapse">◀</span>
    </div>
    """, unsafe_allow_html=True)

    def nav_click(page: str):
        st.session_state.page = page

    sections = [
        ("MAIN", [
            ("◈", "Dashboard", "dashboard"),
            ("🎯", "Opportunities", "dashboard"),
            ("◎", "Targets", "targets"),
            ("📋", "Reports", "reports"),
            ("⟳", "Recon History", "dashboard"),
            ("📡", "Monitor", "dashboard"),
        ]),
        ("INTELLIGENCE", [
            ("⚙", "Acquisition Engine", "dashboard"),
            ("🏆", "Bounty Programs", "dashboard"),
            ("⧫", "Web3 / Crypto", "dashboard"),
            ("⚡", "Technologies", "dashboard"),
            ("🛡", "Attack Surfaces", "attack_surfaces"),
        ]),
        ("TOOLS", [
            ("↻", "Replay Center", "replay"),
            ("⚗", "Parameter Analyzer", "dashboard"),
            ("🔍", "IDOR Engine", "dashboard"),
            ("◈", "GraphQL Explorer", "dashboard"),
        ]),
        ("SETTINGS", [
            ("🔗", "Integrations", "dashboard"),
            ("⚙", "Preferences", "dashboard"),
            ("🔑", "API Keys", "dashboard"),
        ]),
    ]

    for section_name, items in sections:
        st.markdown(f'<div class="nav-section"><div class="nav-section-label">{section_name}</div>', unsafe_allow_html=True)
        for icon, label, page in items:
            active = "active" if st.session_state.page == page else ""
            btn_label = f"{icon} {label}"
            if st.button(btn_label, key=f"nav_{page}_{label}", use_container_width=True, type="tertiary"):
                nav_click(page)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<hr style="margin:4px 0;border-color:#1e2230">', unsafe_allow_html=True)
        st.checkbox("Editor mode", key="editor_mode", help="Show raw DB tables for debugging")

    st.markdown("""
    <div class="sidebar-status">
      <div class="sidebar-status-label">SYSTEM STATUS</div>
      <div class="sidebar-status-text"><span class="sidebar-status-dot"></span> All systems operational</div>
    </div>
    """, unsafe_allow_html=True)

# ── Page Router ───────────────────────────────────
editor_mode = st.session_state.get("editor_mode", False)
_current_page = st.session_state.get("page", "dashboard")

# Normalize page names from sidebar nav
_page_aliases = {"targets": "hot_targets", "reports": "reports",
                 "attack_surfaces": "attack_surfaces", "replay": "replay",
                 "evidence": "evidence", "verdicts": "verdicts",
                 "dashboard": "dashboard"}
_current_page = _page_aliases.get(_current_page, "dashboard")

# Catch-all for unimplemented pages
_coming_soon_pages = {"opportunities", "acquisition_engine", "bounty_programs",
                       "web3_crypto", "technologies", "parameter_analyzer",
                       "idor_engine", "graphql_explorer", "integrations",
                       "preferences", "api_keys", "recon_history", "monitor"}

if _current_page in _coming_soon_pages:
    st.markdown(f'<div class="dark-tab-content"><div style="text-align:center;padding:80px 20px;color:rgba(255,255,255,0.3)"><div style="font-size:48px;margin-bottom:16px">🚧</div><h2 style="color:#fff">Coming Soon</h2><p style="color:rgba(255,255,255,0.4)">This view is not yet implemented.</p></div></div>', unsafe_allow_html=True)
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()
    st.stop()

# Sub-pages (full page renders)
if _current_page == "replay":
    from dashboard.pages.replay import render_replay_page
    render_replay_page(BACKEND_BASE, use_backend)
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"; st.rerun()
    st.stop()

if _current_page == "evidence":
    from dashboard.pages.evidence import render_evidence_page
    render_evidence_page(BACKEND_BASE, use_backend)
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"; st.rerun()
    st.stop()

if _current_page == "verdicts":
    from dashboard.pages.verdicts import render_verdicts_page
    render_verdicts_page(BACKEND_BASE, use_backend)
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"; st.rerun()
    st.stop()

# Main dashboard — show tab bar as styled page buttons
tab_names = ["Dashboard", "Hot Targets", "Attack Surface", "Evidence", "Reports", "Differential"]
if editor_mode:
    tab_names.append("Editor")

_tab_page_map = {"Dashboard": "dashboard", "Hot Targets": "hot_targets",
                  "Attack Surface": "attack_surfaces", "Evidence": "evidence_tab",
                  "Reports": "reports", "Differential": "differential",
                  "Editor": "editor"}
_current_tab_label = next((k for k, v in _tab_page_map.items() if v == _current_page), "Dashboard")

col_tabs = st.columns(len(tab_names))
for i, label in enumerate(tab_names):
    with col_tabs[i]:
        is_active = (label == _current_tab_label)
        btn_style = "primary" if is_active else "tertiary"
        if st.button(label, key=f"tab_{label}", use_container_width=True, type=btn_style):
            st.session_state.page = _tab_page_map[label]
            st.rerun()

st.markdown('<div style="height:4px;background:linear-gradient(90deg,#7c3aed,#a855f7);border-radius:2px;margin-bottom:16px;"></div>', unsafe_allow_html=True)

if _current_page != "dashboard":
    if st.button("← Dashboard", key="back_to_dash", type="tertiary"):
        st.session_state.page = "dashboard"
        st.rerun()

# ── Tab 0 — Mission Control ───────────────────────
if _current_page == "dashboard":
    from dashboard.pages.mission_control import render_mission_control
    render_mission_control(BACKEND_BASE, use_backend)
    st.stop()

# ── Tab 1 — Hot Targets ──────────────────────────
elif _current_page == "hot_targets":
    st.markdown('<div class="dark-tab-content">', unsafe_allow_html=True)
    st.header("Hot Targets")
    st.markdown("Endpoints ranked by risk score (computed by unified engine)")
    mode = st.radio("Source", ["Backend /digest", "Local DB"], horizontal=True, key="hot_targets_source")
    if mode == "Backend /digest":
        digest = safe_fetch("/digest", "Fetching digest")
        if digest and digest.get("high_signal"):
            for item in digest["high_signal"]:
                c = score_color(item["risk_score"])
                st.markdown(f":{c}[**{item['method']} {item['path']}**] — score **{item['risk_score']}** — target {item['target_id']}")
        else:
            st.info("No data. Run a scan first or start the backend.")
    else:
        session = get_session()
        try:
            endpoints = session.query(models.Endpoint).order_by(models.Endpoint.discovered_at.desc()).limit(100).all()
            if not endpoints:
                st.info("No endpoints in DB. Run a scan first.")
            else:
                rows = []
                for ep in endpoints:
                    s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                    rows.append({"id": ep.id, "target_id": ep.target_id, "method": ep.method, "path": ep.path, "score": s["risk_score"], "vector": s["vector"], "actionable": s["actionable"]})
                rows.sort(key=lambda r: r["score"], reverse=True)
                for r in rows[:50]:
                    c = score_color(r["score"])
                    st.markdown(f":{c}[**{r['method']} {r['path']}**] — score **{r['score']}** — vector {r['vector']} — target {r['target_id']}")
        finally:
            session.close()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tab 2 — Attack Surface ───────────────────────
elif _current_page == "attack_surfaces":
    st.markdown('<div class="dark-tab-content">', unsafe_allow_html=True)
    st.header("Attack Surface")
    st.markdown("IDOR clusters, auth boundaries, and multi-tenant zones from unified risk model")
    session = get_session()
    try:
        endpoints = session.query(models.Endpoint).limit(200).all()
        if not endpoints:
            st.info("No endpoints loaded.")
        else:
            scored = []
            for ep in endpoints:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                if s["actionable"]:
                    scored.append({"path": ep.path, "method": ep.method, "risk_score": s["risk_score"], "signals": s.get("signals", []), "attack_surface": s.get("attack_surface", []), "labels": s.get("labels", []), "vector": s.get("vector", ""), "potential_idor": s.get("potential_idor", False)})
            from core.engine.risk_model import AttackSurfaceMapper
            mapper = AttackSurfaceMapper()
            surface = mapper.map(scored)
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"IDOR / BOLA Clusters ({len(surface.idor_clusters)})")
                for ep in surface.idor_clusters[:10]:
                    st.markdown(f"- `{ep['method']} {ep['path']}` — score {ep['risk_score']}")
                if len(surface.idor_clusters) > 10:
                    st.write(f"... and {len(surface.idor_clusters) - 10} more")
                st.subheader(f"Auth Boundaries ({len(surface.auth_boundaries)})")
                for ep in surface.auth_boundaries[:10]:
                    st.markdown(f"- `{ep['method']} {ep['path']}` — score {ep['risk_score']}")
            with col2:
                st.subheader(f"Multi-tenant Zones ({len(surface.multi_tenant_zones)})")
                for ep in surface.multi_tenant_zones[:10]:
                    st.markdown(f"- `{ep['method']} {ep['path']}` — score {ep['risk_score']}")
                st.subheader(f"GraphQL Surfaces ({len(surface.graphql_surfaces)})")
                for ep in surface.graphql_surfaces[:10]:
                    st.markdown(f"- `{ep['method']} {ep['path']}` — score {ep['risk_score']}")
            st.divider()
            with st.expander("Noise Reduction — discarded endpoints"):
                from core.engine.risk_model import NoiseReductionLayer
                nrl = NoiseReductionLayer()
                all_scored = []
                for ep in endpoints:
                    s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                    all_scored.append({**s, "path": ep.path, "method": ep.method})
                nr = nrl.reduce(all_scored)
                _discarded = getattr(nr, 'discarded', [])
                _clean = getattr(nr, 'clean', [])
                _ratio = getattr(nr, 'noise_ratio', 0.0)
                _total = len(_discarded) + len(_clean)
                st.write(f"**{len(_discarded)} discarded** / {_total} total — noise ratio {_ratio:.1%}")
                for d in nr.discarded[:10]:
                    st.code(f"{d.get('method', 'GET')} {d.get('path', '')}")
                if len(nr.discarded) > 10:
                    st.write(f"... and {len(nr.discarded) - 10} more")
            if pd is not None:
                st.divider()
                with st.expander("Endpoint Data Table (Pandas DataFrame)"):
                    df_rows = []
                    for ep in endpoints[:100]:
                        s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                        df_rows.append({"ID": ep.id, "Target": ep.target_id, "Method": ep.method, "Path": ep.path, "Risk Score": round(s["risk_score"], 1), "Vector": s.get("vector", ""), "Actionable": s.get("actionable", False)})
                    if df_rows:
                        df = pd.DataFrame(df_rows)
                        st.dataframe(df, width='stretch', hide_index=True)
    finally:
        session.close()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tab 3 — Evidence ────────────────────────────
elif _current_page == "evidence_tab":
    st.markdown('<div class="dark-tab-content">', unsafe_allow_html=True)
    st.header("Evidence")
    st.markdown("Verdicts, evidence records, and replay")
    ev_tab = st.radio("View", ["Verdicts", "Evidence Records", "Replay"], horizontal=True, key="evidence_tab")
    if ev_tab == "Verdicts":
        st.subheader("Verdicts")
        session = get_session()
        try:
            verdicts = session.query(models.Verdict).order_by(models.Verdict.created_at.desc()).limit(50).all()
            if verdicts:
                for v in verdicts:
                    sm = {"confirmed": "✅", "rejected": "❌", "inconclusive": "⚠️"}
                    icon = sm.get(v.status, "❓")
                    conf = float(v.confidence) if v.confidence else 0.0
                    st.markdown(f"{icon} **{v.status.upper()}** — {v.hot_path_id} — confidence {conf:.0%} — reproducibility {v.reproducibility_score or '?'}")
                    if v.reason: st.caption(v.reason[:200])
                    st.divider()
            else: st.info("No verdicts recorded.")
        finally: session.close()
    elif ev_tab == "Evidence Records":
        st.subheader("Evidence Records")
        session = get_session()
        try:
            evidence = session.query(models.Evidence).order_by(models.Evidence.created_at.desc()).limit(50).all()
            if evidence:
                for ev in evidence[:20]:
                    c = "✅" if ev.consistent == "true" else "❌"
                    st.markdown(f"{c} **{ev.attempt_label}** — status {ev.response_status} — diff {ev.body_diff_ratio or '?'}")
                    if ev.curl_command and len(ev.curl_command) < 2000:
                        with st.expander("Curl"): st.code(ev.curl_command, language="bash")
                    st.divider()
            else: st.info("No evidence captured.")
        finally: session.close()
    else:
        st.subheader("Replay")
        st.markdown("Use the backend API to replay evidence: `POST /verdicts/{id}/replay`")
        verdict_id = st.number_input("Verdict ID", min_value=1, step=1, key="replay_vid")
        attempt_label = st.text_input("Attempt label", "attempt_1", key="replay_attempt")
        if st.button("Replay", key="replay_btn"):
            result = backend_post(f"/verdicts/{verdict_id}/replay", {"attempt_label": attempt_label})
            if result: st.json(result)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tab 4 — Reports ─────────────────────────────
elif _current_page == "reports":
    st.markdown('<div class="dark-tab-content">', unsafe_allow_html=True)
    st.header("Reports")
    st.markdown("Final snapshot-based reports — no recomputation")
    session = get_session()
    try:
        findings = session.query(models.Finding).order_by(models.Finding.created_at.desc()).all()
        if findings:
            for f in findings:
                sev_color = {"critical": "red", "high": "orange", "medium": "yellow", "low": "green"}.get(f.severity or "info", "grey")
                st.markdown(f":{sev_color}[**{f.severity or 'INFO'}**] {f.title} — target {f.target_id}")
                if f.description: st.caption(f.description[:300])
                st.divider()
        else: st.info("No findings yet. Run validation to generate findings and reports.")
        st.subheader("Export")
        if findings:
            export = []
            for f in findings: export.append({"title": f.title, "severity": f.severity, "target_id": f.target_id, "description": f.description})
            st.download_button("Download as JSON", data=json.dumps(export, indent=2), file_name="rastro_findings.json", mime="application/json")
    finally: session.close()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tab 5 — Differential Intelligence ──────────
elif _current_page == "differential":
    st.markdown('<div class="dark-tab-content">', unsafe_allow_html=True)
    st.header("Differential Intelligence")
    st.markdown("Interesting differences and anomalies detected across targets, endpoints, and configurations.")
    st.markdown("")

    col1, col2 = st.columns([1, 4])
    with col1:
        target_id_filter = st.text_input("Target ID (optional)", placeholder="all")
    with col2:
        run_btn = st.button("Run Analysis", type="primary", use_container_width=False)

    if run_btn:
        tid = int(target_id_filter) if target_id_filter.strip().isdigit() else None
        params = f"?target_id={tid}" if tid else ""
        data = safe_fetch(f"/differential-intelligence/analyze{params}", "Running differential analysis")
        if data:
            all_findings = []
            for section in ("target_differences", "endpoint_differences", "historical_changes",
                            "cross_target_patterns", "web3_differences", "interesting_anomalies"):
                all_findings.extend(data.get(section, []))

            st.markdown(f"**Summary:** {data.get('summary', '')}")
            st.markdown(f"**Overall confidence:** {data.get('confidence', 0):.2f}")
            st.markdown("")

            if not all_findings:
                st.info("No differences detected in this analysis.")
            else:
                # Risk breakdown
                risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                for f in all_findings:
                    rl = f.get("risk_level", "low")
                    risk_counts[rl] = risk_counts.get(rl, 0) + 1

                cols = st.columns(4)
                with cols[0]:
                    st.metric("Total Observations", len(all_findings))
                with cols[1]:
                    st.metric("High Risk", risk_counts.get("high", 0) + risk_counts.get("critical", 0))
                with cols[2]:
                    st.metric("Medium Risk", risk_counts.get("medium", 0))
                with cols[3]:
                    st.metric("Low Risk", risk_counts.get("low", 0))

                st.markdown("")

                # Group findings by category
                by_cat: Dict[str, List[Dict]] = {}
                for f in all_findings:
                    cat = f.get("category", "general")
                    by_cat.setdefault(cat, []).append(f)

                cat_labels = {"auth": "🔐 Auth", "idor": "🔑 IDOR", "tenant": "🏢 Multi-tenant",
                              "graphql": "⚡ GraphQL", "api": "🔌 API", "admin": "🛡️ Admin",
                              "export": "📤 Export", "storage": "💾 Storage", "web3": "⛓️ Web3",
                              "oracle": "🔮 Oracle", "bridge": "🌉 Bridge", "contract": "📜 Contract",
                              "configuration": "⚙️ Configuration", "historical": "📋 Historical",
                              "general": "📎 General"}

                tab_list = list(by_cat.keys())
                if tab_list:
                    cat_tabs = st.tabs([cat_labels.get(c, c.title()) for c in tab_list])
                    for i, cat in enumerate(tab_list):
                        with cat_tabs[i]:
                            for f in by_cat[cat]:
                                risk = f.get("risk_level", "low")
                                conf = f.get("confidence", 0)
                                novelty = f.get("novelty_score", 0)
                                priority = f.get("validation_priority", "low")
                                signal_str = ", ".join(f.get("supporting_signals", []))
                                objs_str = ", ".join(f.get("affected_objects", [])[:3])

                                risk_icon = {"critical": "🔥", "high": "⚠️", "medium": "📌", "low": "ℹ️"}
                                icon = risk_icon.get(risk, "ℹ️")

                                st.markdown(
                                    f"{icon} **{f.get('title', '')}** "
                                    f"— risk: {risk}, confidence: {conf:.0%}"
                                )
                                if f.get("description"):
                                    st.markdown(f"  _{f.get('description', '')}_")
                                if objs_str:
                                    st.markdown(f"  Affected: `{objs_str}`")
                                if signal_str:
                                    st.markdown(f"  Signals: `{signal_str}`")
                                if f.get("requires_validation", True):
                                    st.markdown("  ⚠️ Requires validation")
                                st.markdown(
                                    f"  <small>Novelty: {novelty:.2f} | "
                                    f"Priority: {priority}</small>",
                                    unsafe_allow_html=True,
                                )
                                st.markdown("---", unsafe_allow_html=False)
        else:
            st.warning("No data available. Start the backend API and run a scan first.")
    else:
        st.info("Click 'Run Analysis' to detect interesting differences and anomalies.")
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tab 6 — Editor (optional) ──────────────────
elif _current_page == "editor" and editor_mode:
    st.markdown('<div class="dark-tab-content">', unsafe_allow_html=True)
    st.header("Editor")
    st.markdown("Raw database tables for debugging")
    session = get_session()
    try:
        targets = session.query(models.Target).order_by(models.Target.created_at.desc()).all()
        st.subheader(f"Targets ({len(targets)})")
        for t in targets: st.write(f"#{t.id} {t.name} — {t.domain or '-'}")
        endpoints = session.query(models.Endpoint).order_by(models.Endpoint.discovered_at.desc()).limit(20).all()
        st.subheader(f"Endpoints ({len(endpoints)} shown)")
        for ep in endpoints: st.write(f"#{ep.id} {ep.method} {ep.path} — target {ep.target_id}")
    finally: session.close()
    st.markdown('</div>', unsafe_allow_html=True)
