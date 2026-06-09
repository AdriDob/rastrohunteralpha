"""
Dashboard page: Verdicts viewer.

Shows all validation verdicts with filtering and drill-down into evidence.
"""
import json
from datetime import datetime

import requests
import streamlit as st


def render_verdicts_page(backend_base: str, use_backend: bool):
    """Render verdicts tab."""
    st.header("🎯 Verdicts")
    
    if not use_backend or not backend_base:
        st.warning("Backend not configured")
        return
    
    try:
        # Fetch verdicts
        resp = requests.get(
            f"{backend_base}/verdicts",
            params={"limit": 100},
            timeout=10,
        )
        resp.raise_for_status()
        verdicts = resp.json()
    except Exception as e:
        st.error(f"Failed to fetch verdicts: {str(e)}")
        return
    
    if not verdicts:
        st.info("No verdicts recorded yet")
        return
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    confirmed = sum(1 for v in verdicts if v.get("status") == "confirmed")
    rejected = sum(1 for v in verdicts if v.get("status") == "rejected")
    inconclusive = sum(1 for v in verdicts if v.get("status") == "inconclusive")
    total = len(verdicts)
    
    with col1:
        st.metric("Total Verdicts", total)
    with col2:
        st.metric("✅ Confirmed", confirmed, f"{100*confirmed//total if total else 0}%")
    with col3:
        st.metric("❌ Rejected", rejected, f"{100*rejected//total if total else 0}%")
    with col4:
        st.metric("❓ Inconclusive", inconclusive, f"{100*inconclusive//total if total else 0}%")
    
    st.divider()
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.multiselect(
            "Status",
            options=["confirmed", "rejected", "inconclusive"],
            default=["confirmed"],
        )
    with col2:
        filter_confidence_min = st.slider("Min Confidence", 0.0, 1.0, 0.6)
    with col3:
        filter_hot_path = st.text_input("Hot Path Filter", placeholder="e.g., idor")
    
    # Filter verdicts
    filtered = verdicts
    filtered = [v for v in filtered if v.get("status") in filter_status]
    filtered = [v for v in filtered if v.get("confidence", 0) >= filter_confidence_min]
    if filter_hot_path:
        filtered = [v for v in filtered if filter_hot_path.lower() in v.get("hot_path_id", "").lower()]
    
    st.divider()
    
    # Display table
    st.subheader(f"Results ({len(filtered)} of {total})")
    
    for verdict in filtered:
        with st.expander(
            f"[{verdict['status'].upper()}] {verdict['hot_path_id']} "
            f"(confidence: {verdict['confidence']:.2%})",
            expanded=False,
        ):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Confidence", f"{verdict['confidence']:.2%}")
            with col2:
                st.metric("Reproducibility", f"{verdict['reproducibility_score']:.2%}")
            with col3:
                st.metric("Attempts", verdict.get("retry_count", 3))
            
            st.subheader("Validation Report")
            report = verdict.get("validation_report", {})
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Passed Rules:**")
                for rule in report.get("passed_rules", []):
                    st.write(f"✅ {rule}")
            with col2:
                st.write("**Failed Rules:**")
                for rule in report.get("failed_rules", []):
                    st.write(f"❌ {rule}")
            
            st.write("**Reason:**")
            st.write(verdict.get("reason", "N/A"))
            
            # Link to evidence
            if st.button(f"View Evidence → {verdict['hot_path_id']}", key=f"evidence_{verdict['hot_path_id']}"):
                st.session_state["selected_verdict_id"] = verdict.get("id")
                st.session_state["page"] = "evidence"
                st.rerun()
