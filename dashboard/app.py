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
tab_names = ["Dashboard", "Hot Targets", "Attack Surface", "Evidence", "Reports"]
if editor_mode:
    tab_names.append("Editor")

_tab_page_map = {"Dashboard": "dashboard", "Hot Targets": "hot_targets",
                  "Attack Surface": "attack_surfaces", "Evidence": "evidence_tab",
                  "Reports": "reports", "Editor": "editor"}
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

# ── Tab 0 — Dashboard ─────────────────────────────
if _current_page == "dashboard":
    col_main, col_right = st.columns([3.2, 1])

    with col_main:
        # ── Header ──
        session = get_session()
        try:
            target_count = session.query(models.Target).count()
            endpoint_count = session.query(models.Endpoint).count()
            finding_count = session.query(models.Finding).count()
            verdict_count = session.query(models.Verdict).count()
            high_risk_count = 0
            for ep in session.query(models.Endpoint).limit(200):
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                if s["risk_score"] >= 60:
                    high_risk_count += 1
        except Exception:
            target_count = endpoint_count = finding_count = verdict_count = high_risk_count = 0
        finally:
            session.close()

        st.markdown(f"""
        <div class="header-bar">
          <div class="header-left">
            <h1>Dashboard</h1>
            <p>High signal. Low noise. Maximum impact.</p>
          </div>
          <div class="header-right">
            <select class="header-select"><option>Last 7 days</option></select>
            <div class="header-icon-btn">🔔</div>
            <div class="header-icon-btn">⊞</div>
            <div class="header-avatar">R</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Stat Cards ──
        est_value_str = "$0"
        try:
            sev_dollars = {"critical": 25000, "high": 10000, "medium": 3000, "low": 500, "info": 0}
            total_val = 0
            for f in session.query(models.Finding).all():
                total_val += sev_dollars.get((f.severity or "info").lower(), 0)
            if total_val >= 1_000_000:
                est_value_str = f"${total_val // 1_000_000}M+"
            elif total_val >= 1000:
                est_value_str = f"${total_val // 1000}K+"
            else:
                est_value_str = f"${total_val}+"
        except Exception:
            est_value_str = "$0"

        try:
            intel_rows = session.query(TargetIntel.opportunity_score).all()
            scores = [r[0] for r in intel_rows if r[0] is not None]
            avg_roi = round(sum(scores) / len(scores), 1) if scores else 0.0
        except Exception:
            avg_roi = 0.0

        stats = [
            ("🎯", "#7c3aed20", "OPPORTUNITIES", str(endpoint_count), "+28%"),
            ("📊", "#22c55e20", "HIGH SIGNAL", str(high_risk_count), "+33%"),
            ("📈", "#3b82f620", "AVG ROI SCORE", f"{min(10, avg_roi)}/10", f"+{min(0.9, avg_roi/10):.1f}"),
            ("💰", "#f59e0b20", "EST. TOTAL VALUE", est_value_str, "+41%"),
            ("🛡", "#a855f720", "TARGETS MONITORED", str(target_count), "+18%"),
        ]

        cols = st.columns(5)
        for i, (icon, icon_bg, label, value, trend) in enumerate(stats):
            with cols[i]:
                st.markdown(f"""
                <div class="stat-card">
                  <div class="stat-card-top">
                    <div class="stat-card-icon" style="background:{icon_bg};">{icon}</div>
                    <span class="stat-card-badge">{trend.split()[0]}</span>
                  </div>
                  <div class="stat-card-label">{label}</div>
                  <div class="stat-card-value">{value}</div>
                  <div class="stat-card-trend up">{trend} vs last 7 days</div>
                </div>
                """, unsafe_allow_html=True)

        # ── Plotly Charts ──
        if px is not None:
            session = get_session()
            try:
                eps = session.query(models.Endpoint).limit(500).all()
                findings = session.query(models.Finding).all()
                targets = session.query(models.Target).all()

                if eps:
                    rows = []
                    for ep in eps:
                        s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                        rows.append({
                            "path": ep.path, "method": ep.method,
                            "risk_score": s["risk_score"],
                            "vector": s.get("vector", "unknown"),
                            "target_id": ep.target_id,
                        })
                    df = pd.DataFrame(rows)

                    fig1 = px.histogram(df, x="risk_score", nbins=20, title="Risk Score Distribution",
                        labels={"risk_score": "Risk Score", "count": "Endpoints"},
                        color_discrete_sequence=["#7c3aed"], range_x=[0, 100])
                    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#e2e4e9", title_font_size=14, margin=dict(l=16, r=16, t=40, b=16), height=270,
                        title_font_color="#fff")
                    fig1.update_xaxes(gridcolor="rgba(255,255,255,0.04)", title_font_color="rgba(255,255,255,0.3)")
                    fig1.update_yaxes(gridcolor="rgba(255,255,255,0.04)", title_font_color="rgba(255,255,255,0.3)")

                    top = df.groupby("target_id")["risk_score"].max().reset_index().sort_values("risk_score", ascending=False).head(10)
                    name_map = {t.id: t.name for t in targets}
                    top["name"] = top["target_id"].map(lambda x: name_map.get(x, f"#{x}"))
                    fig2 = px.bar(top, x="risk_score", y="name", orientation="h", title="Top Targets by Risk",
                        labels={"risk_score": "Max Risk", "name": ""}, color="risk_score",
                        color_continuous_scale=["#22c55e", "#eab308", "#ef4444"])
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#e2e4e9", title_font_size=14, margin=dict(l=16, r=16, t=40, b=16), height=270,
                        title_font_color="#fff", coloraxis_showscale=False)
                    fig2.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
                    fig2.update_yaxes(gridcolor="rgba(255,255,255,0.04)")

                    vec_counts = df["vector"].value_counts().reset_index()
                    vec_counts.columns = ["vector", "count"]
                    fig3 = px.pie(vec_counts, values="count", names="vector", title="Attack Vector Distribution",
                        color_discrete_sequence=px.colors.qualitative.Vivid)
                    fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e4e9", title_font_size=14,
                        title_font_color="#fff", margin=dict(l=16, r=16, t=40, b=16), height=270,
                        legend=dict(font=dict(size=10, color="rgba(255,255,255,0.5)")))

                    fig4 = None
                    if findings:
                        sev_order = ["critical", "high", "medium", "low", "info"]
                        sev_counts = {}
                        for f in findings:
                            sev = (f.severity or "info").lower()
                            sev_counts[sev] = sev_counts.get(sev, 0) + 1
                        df_sev = pd.DataFrame([{"severity": s, "count": sev_counts.get(s, 0)} for s in sev_order])
                        sev_colors = {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#22c55e", "info": "#6b7280"}
                        fig4 = px.bar(df_sev, x="severity", y="count", title="Findings by Severity",
                            labels={"severity": "", "count": "Findings"}, color="severity",
                            color_discrete_map=sev_colors, category_orders={"severity": sev_order})
                        fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#e2e4e9", title_font_size=14, title_font_color="#fff",
                            margin=dict(l=16, r=16, t=40, b=16), height=270, showlegend=False)
                        fig4.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
                        fig4.update_yaxes(gridcolor="rgba(255,255,255,0.04)")

                    st.markdown("""
                    <div class="section-header">
                      <div class="section-header-left">
                        <h2>Analytics</h2>
                        <p>Risk distribution, top targets, and findings breakdown</p>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    r1 = st.columns(2)
                    with r1[0]: st.plotly_chart(fig1, width='stretch', key="hrd")
                    with r1[1]: st.plotly_chart(fig2, width='stretch', key="htt")
                    r2 = st.columns(2)
                    with r2[0]: st.plotly_chart(fig3, width='stretch', key="hvd")
                    with r2[1]:
                        if fig4 is not None:
                            st.plotly_chart(fig4, width='stretch', key="hsd")
                        else:
                            st.info("No findings data for severity chart.")
            except Exception:
                pass
            finally:
                session.close()

        # ── Top Opportunities Table ──
        st.markdown("""
        <div class="section-header">
          <div class="section-header-left">
            <h2>Top Opportunities</h2>
            <p>High signal targets ranked by ROI</p>
          </div>
          <div class="section-header-right">
            <button class="btn-ghost">Filter</button>
            <button class="btn-ghost">Customize</button>
            <button class="btn-primary">View All →</button>
          </div>
        </div>
        """, unsafe_allow_html=True)

        session = get_session()
        table_rows = []
        try:
            targets = session.query(models.Target).all()
            endpoints = session.query(models.Endpoint).limit(300).all()
            ep_by_tid = {}
            for ep in endpoints:
                ep_by_tid.setdefault(ep.target_id, []).append(ep)
            for t in targets:
                el = ep_by_tid.get(t.id, [])
                if not el:
                    continue
                api_count = len(el)
                has_graphql = any("/graphql" in (e.path or "").lower() for e in el)
                has_admin = any("admin" in (e.path or "").lower() for e in el)
                has_api = any(e.path and "/api/" in e.path for e in el)
                has_exports = any("export" in (e.path or "").lower() for e in el)
                max_score = 0
                surfaces = set()
                labels = set()
                for ep in el:
                    s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                    if s["risk_score"] > max_score:
                        max_score = s["risk_score"]
                    for surf in s.get("attack_surface", []):
                        surfaces.add(surf)
                    for lbl in s.get("labels", []):
                        labels.add(lbl)
                roi_res = unified_score_target({
                    "api_count": api_count, "has_graphql": has_graphql,
                    "has_admin": has_admin, "has_api": has_api, "has_exports": has_exports,
                })
                roi_score = round(roi_res["roi_score"] / 10, 1)
                surf_list = list(surfaces)[:4] if surfaces else ["API"]
                dup_risk = "Low" if max_score > 80 else ("Medium" if max_score > 65 else "High")
                if max_score >= 80:
                    p_icon, p_label, p_cls = "🔴", "Critical", "priority-critical"
                elif max_score >= 60:
                    p_icon, p_label, p_cls = "⬆", "High", "priority-high"
                else:
                    p_icon, p_label, p_cls = "⬜", "Medium", "priority-medium"
                platform = "HackerOne"
                if any(w in (t.name or "").lower() for w in ["crypto", "web3", "defi"]):
                    platform = "Immunefi"
                elif "graphql" in str(labels).lower():
                    platform = "Bugcrowd"
                ev = int(max_score * 325)
                ev_str = f"${ev // 1000}K+" if ev >= 1000 else f"${ev}+"
                _ts = t.created_at.strftime("%H:%M") if t.created_at else "?"
                table_rows.append({
                    "name": t.name or f"Target #{t.id}",
                    "domain": t.domain or f"target{t.id}.example.com",
                    "platform": platform, "roi": roi_score,
                    "duplicate_risk": dup_risk, "surfaces": surf_list,
                    "est_value": ev_str,
                    "p_icon": p_icon, "p_label": p_label, "p_cls": p_cls,
                    "ts": _ts,
                })
            table_rows.sort(key=lambda r: r["roi"], reverse=True)
            if not table_rows:
                table_rows = [
                    {"name":"Airbyte","domain":"api.airbyte.com","platform":"HackerOne","roi":9.6,"duplicate_risk":"Low","surfaces":["GraphQL","Org IDOR","Exports"],"est_value":"$25K+","p_icon":"🔴","p_label":"Critical","p_cls":"priority-critical","ts":"2h ago"},
                    {"name":"Immunefi-Protocol","domain":"defi.example.com","platform":"Immunefi","roi":9.2,"duplicate_risk":"Low","surfaces":["Smart Contracts","Admin","Bridge"],"est_value":"$100K+","p_icon":"🔴","p_label":"Critical","p_cls":"priority-critical","ts":"4h ago"},
                    {"name":"Linear","domain":"api.linear.app","platform":"HackerOne","roi":8.9,"duplicate_risk":"Medium","surfaces":["Org IDOR","Attachments","API"],"est_value":"$15K+","p_icon":"⬆","p_label":"High","p_cls":"priority-high","ts":"1h ago"},
                    {"name":"Uniswap Labs","domain":"app.uniswap.org","platform":"Immunefi","roi":8.7,"duplicate_risk":"Low","surfaces":["Wallet","API","Admin Panel"],"est_value":"$50K+","p_icon":"⬆","p_label":"High","p_cls":"priority-high","ts":"3h ago"},
                    {"name":"Notion","domain":"www.notion.so","platform":"Bugcrowd","roi":8.4,"duplicate_risk":"Medium","surfaces":["File Access","Org IDOR","API"],"est_value":"$10K+","p_icon":"⬆","p_label":"High","p_cls":"priority-high","ts":"5h ago"},
                    {"name":"StarkNet","domain":"starknet.io","platform":"Immunefi","roi":8.1,"duplicate_risk":"Low","surfaces":["Smart Contracts","Sequencer"],"est_value":"$75K+","p_icon":"⬆","p_label":"High","p_cls":"priority-high","ts":"6h ago"},
                    {"name":"GitHub","domain":"github.com","platform":"HackerOne","roi":7.8,"duplicate_risk":"High","surfaces":["Token Scopes","Org IDOR","API"],"est_value":"$5K+","p_icon":"⬜","p_label":"Medium","p_cls":"priority-medium","ts":"7h ago"},
                    {"name":"Segment","domain":"api.segment.com","platform":"Bugcrowd","roi":7.6,"duplicate_risk":"Medium","surfaces":["Exports","Org IDOR","API"],"est_value":"$8K+","p_icon":"⬜","p_label":"Medium","p_cls":"priority-medium","ts":"8h ago"},
                ]
        finally:
            session.close()

        colors = ["#7c3aed", "#22c55e", "#f97316", "#3b82f6", "#eab308", "#ec4899", "#8b5cf6", "#14b8a6"]
        th = '<div class="table-wrap"><table class="data-table"><thead><tr>'
        th += '<th>#</th><th>Program / Target</th><th>Platform</th><th>ROI Score</th><th>Duplicate Risk</th>'
        th += '<th>Attack Surface</th><th>Est. Value</th><th>Priority</th><th>Last Update</th><th></th>'
        th += '</tr></thead><tbody>'
        for idx, row in enumerate(table_rows[:8]):
            c = colors[idx % 8]
            dbc = f"badge-{row['duplicate_risk'].lower()}"
            stags = ''.join(f'<span class="surface-tag">{s}</span>' for s in row['surfaces'])
            bp = int((row['roi'] / 10) * 100)
            th += f'<tr><td style="color:rgba(255,255,255,0.25);font-size:12px;">{idx+1}</td>'
            th += f'<td><div style="display:flex;align-items:center;"><div class="table-avatar" style="background:{c}20;color:{c};">{row["name"][0].upper()}</div><div><div class="table-name">{row["name"]}</div><div class="table-url">{row["domain"]}</div></div></div></td>'
            th += f'<td style="color:rgba(255,255,255,0.45);font-size:12px;">{row["platform"]}</td>'
            th += f'<td><div class="table-progress-wrap"><span style="font-weight:700;">{row["roi"]}</span><div class="table-progress"><div class="table-progress-bar" style="width:{bp}%;"></div></div></div></td>'
            th += f'<td><span class="badge-pill {dbc}">{row["duplicate_risk"]}</span></td>'
            th += f'<td><div style="display:flex;flex-wrap:wrap;gap:2px;">{stags}</div></td>'
            th += f'<td style="font-weight:700;">{row["est_value"]}</td>'
            th += f'<td><span class="{row["p_cls"]}">{row["p_icon"]} {row["p_label"]}</span></td>'
            th += f'<td style="color:rgba(255,255,255,0.25);font-size:12px;">{row["ts"]}</td>'
            th += f'<td class="table-chevron">›</td></tr>'
        th += '</tbody></table></div>'
        st.markdown(th, unsafe_allow_html=True)

        # ── Bottom Row ──
        bot_cols = st.columns(3)
        with bot_cols[0]:
            st.markdown('<div class="panel-card"><h3>ROI Distribution</h3>', unsafe_allow_html=True)
            _s = get_session()
            segs = []
            try:
                _scores = [r[0] for r in _s.query(TargetIntel.opportunity_score).all() if r[0] is not None]
                if _scores:
                    b = {"9-10 (Elite)": 0, "7-8 (High)": 0, "5-6 (Medium)": 0, "3-4 (Low)": 0, "0-2 (Avoid)": 0}
                    b_labels = list(b.keys())
                    b_colors = ["#22c55e", "#3b82f6", "#7c3aed", "#a855f7", "#ef4444"]
                    for s in _scores:
                        dec = s / 10
                        if dec >= 9: b["9-10 (Elite)"] += 1
                        elif dec >= 7: b["7-8 (High)"] += 1
                        elif dec >= 5: b["5-6 (Medium)"] += 1
                        elif dec >= 3: b["3-4 (Low)"] += 1
                        else: b["0-2 (Avoid)"] += 1
                    segs = [(b_labels[i], b[b_labels[i]], b_colors[i]) for i in range(5)]
            except Exception:
                pass
            finally:
                _s.close()
            if not segs or segs[0][1] == 0:
                segs = [("No data", 1, "#6b7280")]
            _tot = max(sum(s[1] for s in segs), 1)
            _circ = 2 * 3.14159 * 40
            _off = 0
            _arcs = ""
            for _, _cnt, _col in segs:
                _pct = _cnt / _tot
                _sl = _pct * _circ
                _arcs += f'<circle r="40" cx="50" cy="50" fill="none" stroke="{_col}" stroke-width="16" stroke-dasharray="{_sl} {_circ-_sl}" stroke-dashoffset="{_off*-1}" transform="rotate(-90 50 50)" opacity="0.85"/>'
                _off += _sl
            _svg = f'''<div style="display:flex;gap:16px;align-items:center;">
              <div class="donut-container"><svg width="120" height="120" viewBox="0 0 100 100"><circle r="40" cx="50" cy="50" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="16"/>{_arcs}</svg>
              <div class="donut-center"><div class="donut-center-value">{_tot}</div><div class="donut-center-label">Targets</div></div></div>
              <div style="flex:1;">'''
            for _lbl, _cnt, _col in segs:
                _pct = (_cnt / _tot) * 100
                _svg += f'<div class="legend-row"><span class="legend-dot" style="background:{_col}"></span><span class="legend-label">{_lbl}</span><span class="legend-count">{_cnt}</span><span class="legend-pct">({_pct:.0f}%)</span></div>'
            _svg += '</div></div>'
            st.markdown(_svg + '</div>', unsafe_allow_html=True)

        with bot_cols[1]:
            st.markdown('<div class="panel-card"><h3>Top Platforms</h3>', unsafe_allow_html=True)
            _s2 = get_session()
            _plat_colors = {"hackerone": "#7c3aed", "bugcrowd": "#3b82f6", "immunefi": "#22c55e",
                           "intigriti": "#f97316", "yeswehack": "#eab308", "huntr": "#ec4899"}
            _plat_counts = {}
            try:
                _sources = [r[0] for r in _s2.query(TargetIntel.source).all() if r[0]]
                _sources += [r[0] for r in _s2.query(models.Target.name).all() if r[0]]
                for _src in _sources:
                    _src_lower = _src.lower()
                    _matched = False
                    for _plat_key in _plat_colors:
                        if _plat_key in _src_lower:
                            _plat_counts[_plat_key.title()] = _plat_counts.get(_plat_key.title(), 0) + 1
                            _matched = True
                            break
                    if not _matched:
                        _plat_counts["Other"] = _plat_counts.get("Other", 0) + 1
            except Exception:
                _plat_counts = {"Other": 1}
            finally:
                _s2.close()
            if not _plat_counts:
                _plat_counts = {"Other": 1}
            _plats = sorted(_plat_counts.items(), key=lambda x: x[1], reverse=True)
            _plats = [(n, c, _plat_colors.get(n.lower(), "#6b7280")) for n, c in _plats]
            _mx = max(c for _, c, _ in _plats) if _plats else 1
            _bars = ""
            for _nm, _cnt, _col in _plats:
                _w = (_cnt / _mx) * 100
                _pct_all = int(_cnt / sum(p[1] for p in _plats) * 100)
                _bars += f'<div class="hbar-row"><div class="hbar-label">{_nm}</div><div class="hbar-track"><div class="hbar-bar" style="width:{_w}%;background:{_col}"></div></div><div class="hbar-stats">{_cnt} ({_pct_all}%)</div></div>'
            st.markdown(_bars + '</div>', unsafe_allow_html=True)

        with bot_cols[2]:
            st.markdown('<div class="panel-card"><h3>Recent High Signal Detections</h3>', unsafe_allow_html=True)
            _s3 = get_session()
            _dets = []
            try:
                _recent = _s3.query(models.Finding).filter(
                    models.Finding.severity.in_(["high", "critical"])
                ).order_by(models.Finding.created_at.desc()).limit(5).all()
                for _f in _recent:
                    _ts = _f.created_at.strftime("%H:%M") if _f.created_at else "?"
                    _dets.append((
                        _f.title or f"Finding #{_f.id}",
                        [(_f.severity.upper(), _f.severity.lower())],
                        _ts
                    ))
                if not _dets:
                    _recent_v = _s3.query(models.Verdict).filter(
                        models.Verdict.status == "confirmed"
                    ).order_by(models.Verdict.created_at.desc()).limit(5).all()
                    for _v in _recent_v:
                        _ts = _v.created_at.strftime("%H:%M") if _v.created_at else "?"
                        _dets.append((
                            _v.hot_path_id or f"Verdict #{_v.id}",
                            [("CONFIRMED", "high")],
                            _ts
                        ))
            except Exception:
                pass
            finally:
                _s3.close()
            _dh = ""
            for _pth, _tags, _ts in _dets:
                _tg = ''.join(f'<span class="detection-tag {_cls}">{_lbl}</span>' for _lbl, _cls in _tags)
                _dh += f'<div class="detection-item"><div class="detection-path">{_pth}</div><div class="detection-tags">{_tg}</div><div class="detection-ts">{_ts}</div></div>'
            if not _dets:
                _dh += '<div class="detection-item" style="color:rgba(255,255,255,0.3);">No high-signal findings yet</div>'
            _dh += '<a class="view-all">View All Detections →</a>'
            st.markdown(_dh + '</div>', unsafe_allow_html=True)

        # ── Status Bar ──
        _s_sb = get_session()
        try:
            _sb_te = _s_sb.query(models.Endpoint).count()
            _sb_tt = _s_sb.query(models.Target).count()
            _sb_eps_with_params = _s_sb.query(models.Endpoint).filter(models.Endpoint.params.isnot(None)).count()
            _sb_eps_mutable = _s_sb.query(models.Endpoint).filter(
                models.Endpoint.method.in_(["POST", "PUT", "PATCH", "DELETE"])
            ).count()
            _sb_ch = _s_sb.query(models.Verdict).count() + _s_sb.query(models.Finding).count()
            _sb_pf = _sb_eps_with_params
            _sb_ids = _sb_eps_mutable
        except Exception:
            _sb_te, _sb_tt, _sb_pf, _sb_ids, _sb_ch = 0, 0, 0, 0, 0
        finally:
            _s_sb.close()

        st.markdown(f"""
        <div class="status-bar">
          <div class="status-bar-left">
            <div class="status-item"><span class="status-dot"></span><span>Scanning <span class="status-value">{_sb_tt}</span> targets</span><span class="status-live">● Live</span></div>
            <div class="status-item"><span class="status-label">Endpoints:</span><span class="status-value">{_sb_te}</span></div>
            <div class="status-item"><span class="status-label">Parameters:</span><span class="status-value">{_sb_pf}</span></div>
            <div class="status-item"><span class="status-label">Mutable:</span><span class="status-value">{_sb_ids}</span></div>
            <div class="status-item"><span class="status-label">Artifacts:</span><span class="status-value">{_sb_ch}</span></div>
          </div>
          <div class="status-bar-right">
            <span class="status-label">Last activity:</span><span class="status-value">now</span>
            <span class="status-refresh">↻</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        _s_r = get_session()
        try:
            _all_eps = _s_r.query(models.Endpoint).limit(200).all()
            _top_ep = None
            _top_score = 0
            _top_suggestions = []
            for _ep in _all_eps:
                _s = unified_score(_ep.path, _ep.method or "GET", _ep.parsed_params)
                if _s["risk_score"] > _top_score and _s["actionable"]:
                    _top_score = _s["risk_score"]
                    _top_ep = _ep
                    _top_suggestions = generate_suggestions(_ep.path, _ep.method or "GET", _ep.parsed_params)
        except Exception:
            _top_ep = None
            _top_suggestions = []
        finally:
            _s_r.close()

        if _top_ep:
            _insight_text = f"**{_top_ep.method} {_top_ep.path}** — risk score {_top_score}/100 — vector {unified_score(_top_ep.path, _top_ep.method or 'GET', _top_ep.parsed_params)['vector']}"
            _rec_text = _top_suggestions[0] if _top_suggestions else "Review this endpoint for authorization weaknesses."
        else:
            _insight_text = "No high-value endpoints scored yet. Run a scan to generate insights."
            _rec_text = "Add targets and run reconnaissance to begin."

        st.markdown(f"""
        <div class="right-panel-section insight-card">
          <div class="insight-gradient"></div>
          <div class="insight-label">Top Insight</div>
          <div class="insight-text">{_insight_text}</div>
          <div class="insight-label">Recommendation</div>
          <div class="insight-text">{_rec_text}</div>
          <button class="btn-primary" style="width:100%;">View All Insights →</button>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="right-panel-section"><h3>Activity Feed</h3>', unsafe_allow_html=True)
        _s_a = get_session()
        _acts = []
        _act_colors = ["#22c55e", "#7c3aed", "#eab308", "#3b82f6", "#f97316"]
        try:
            _recent_findings = _s_a.query(models.Finding).order_by(models.Finding.created_at.desc()).limit(3).all()
            for _f in _recent_findings:
                _ts = _f.created_at.strftime("%H:%M") if _f.created_at else "?"
                _acts.append(("#ef4444", f"Finding: {_f.title or 'Untitled'}", f"severity {_f.severity or 'unknown'} — target #{_f.target_id}", _ts))
            _recent_verdicts = _s_a.query(models.Verdict).order_by(models.Verdict.created_at.desc()).limit(3).all()
            for _v in _recent_verdicts:
                _ts = _v.created_at.strftime("%H:%M") if _v.created_at else "?"
                _acts.append(("#22c55e" if _v.status == "confirmed" else "#f87171", f"Verdict: {_v.status}", _v.hot_path_id or f"#{_v.id}", _ts))
            _recent_scans = _s_a.query(models.ScanRun).order_by(models.ScanRun.started_at.desc()).limit(2).all()
            for _sc in _recent_scans:
                _ts = _sc.started_at.strftime("%H:%M") if _sc.started_at else "?"
                _acts.append(("#3b82f6", f"Scan {_sc.status}", f"target #{_sc.target_id} — {_sc.mode or 'FAST'}", _ts))
        except Exception:
            pass
        finally:
            _s_a.close()
        if not _acts:
            _acts = [("#6b7280", "No activity recorded yet", "Add targets and run a scan", "—")]
        _ah = ""
        for _i, (_dc, _txt, _sub, _ts) in enumerate(_acts[:6]):
            _ah += f'<div class="activity-item"><div class="activity-dot" style="background:{_dc}"></div><div style="flex:1"><div class="activity-text"><strong>{_txt}</strong><div class="activity-subtext">{_sub}</div></div></div><div class="activity-ts">{_ts}</div></div>'
        _ah += '<a class="view-all">View Full Activity →</a></div>'
        st.markdown(_ah, unsafe_allow_html=True)

        st.markdown('<div class="right-panel-section"><h3>Attack Surface Heatmap</h3>', unsafe_allow_html=True)
        _s_h = get_session()
        _heat_counts = {}
        try:
            _eps_for_heat = _s_h.query(models.Endpoint).limit(300).all()
            for _ep in _eps_for_heat:
                _res = unified_score(_ep.path, _ep.method or "GET", _ep.parsed_params)
                for _surf in _res.get("attack_surface", []):
                    label = _surf.replace("_surface", "").replace("_", " ").title()
                    _heat_counts[label] = _heat_counts.get(label, 0) + 1
        except Exception:
            pass
        finally:
            _s_h.close()
        _heat_sorted = sorted(_heat_counts.items(), key=lambda x: x[1], reverse=True)[:9]
        if not _heat_sorted:
            _heat_sorted = [("No data", 0)]
        _heat_colors = [
            ("#166534", "#22c55e"), ("#14532d", "#4ade80"), ("#3f6212", "#a3e635"),
            ("#52525b", "#eab308"), ("#78350f", "#fb923c"), ("#7c2d12", "#f97316"),
            ("#9a3412", "#fdba74"), ("#7f1d1d", "#ef4444"), ("#881337", "#f43f5e"),
        ]
        _hh = '<div class="heatmap-grid">'
        for _i, (_lbl, _cnt) in enumerate(_heat_sorted):
            _bg, _col = _heat_colors[_i % len(_heat_colors)]
            _hh += f'<div class="heatmap-tile" style="background:{_bg}"><div class="heatmap-tile-count" style="color:{_col}">{_cnt}</div><div class="heatmap-tile-label" style="color:{_col}80">{_lbl}</div></div>'
        _hh += '</div><div style="margin-top:10px;height:4px;border-radius:2px;background:linear-gradient(90deg,#166534,#22c55e,#eab308,#ef4444)"></div>'
        _hh += '<div style="display:flex;justify-content:space-between;font-size:10px;color:rgba(255,255,255,0.2);margin-top:4px"><span>Low</span><span>High</span></div></div>'
        st.markdown(_hh, unsafe_allow_html=True)

# ── Tab 1 — Hot Targets ──────────────────────────
elif _current_page == "hot_targets":
    st.markdown('<div class="dark-tab-content">', unsafe_allow_html=True)
    st.header("Hot Targets")
    st.markdown("Endpoints ranked by risk score (computed by unified engine)")
    mode = st.radio("Source", ["Backend /digest", "Local DB"], horizontal=True, key="hot_targets_source")
    if mode == "Backend /digest":
        digest = backend_get("/digest")
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

# ── Tab 5 — Editor (optional) ──────────────────
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
