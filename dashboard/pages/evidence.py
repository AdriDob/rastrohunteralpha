"""
Dashboard page: Evidence viewer.

Shows request/response pairs with diffs and curl commands.
"""
import json

import requests
import streamlit as st


def render_evidence_page(backend_base: str, use_backend: bool):
    """Render evidence viewer tab."""
    st.header("🔍 Evidence Viewer")
    
    if not use_backend or not backend_base:
        st.warning("Backend not configured")
        return
    
    # Verdict selector
    verdict_id = st.number_input("Verdict ID", min_value=1, step=1)
    
    if not st.button("Load Evidence"):
        return
    
    try:
        resp = requests.get(
            f"{backend_base}/verdicts/{verdict_id}/evidence",
            timeout=10,
        )
        resp.raise_for_status()
        evidence_data = resp.json()
    except Exception as e:
        st.error(f"Failed to fetch evidence: {str(e)}")
        return
    
    if not evidence_data or "attempts" not in evidence_data:
        st.warning("No evidence found for this verdict")
        return
    
    # Summary
    st.subheader("Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Attempts", evidence_data.get("total_attempts", 0))
    with col2:
        summary = evidence_data.get("summary", {})
        st.metric(
            "Consistency", 
            f"{summary.get('consistency_ratio', 0):.2%}"
        )
    with col3:
        st.metric(
            "Avg Body Diff", 
            f"{summary.get('average_body_diff_ratio', 0):.2%}"
        )
    
    st.divider()
    
    # Attempt selector
    attempts = evidence_data.get("attempts", [])
    attempt_labels = [a.get("attempt", f"Attempt {i}") for i, a in enumerate(attempts)]
    selected_attempt_idx = st.selectbox(
        "Select Attempt",
        range(len(attempts)),
        format_func=lambda i: attempt_labels[i],
    )
    
    if selected_attempt_idx >= len(attempts):
        st.warning("Invalid attempt selected")
        return
    
    attempt = attempts[selected_attempt_idx]
    
    st.divider()
    
    # Display tabs: Request, Response, Diff, Curl
    tab1, tab2, tab3, tab4 = st.tabs(["Request", "Response", "Diff", "Curl"])
    
    with tab1:
        st.subheader("Request")
        st.write(f"**Status:** {attempt.get('status_code')}")
        st.write(f"**Consistent:** {attempt.get('consistent')}")
        st.write(f"**Body Diff Ratio:** {attempt.get('body_diff_ratio')}")
        st.write(f"**Sensitive Fields:** {', '.join(attempt.get('sensitive_fields', []))}")
    
    with tab2:
        st.subheader("Response")
        response_status = attempt.get("status_code", "N/A")
        st.write(f"**Status Code:** {response_status}")
        st.write(f"**Sensitive Fields Detected:** {', '.join(attempt.get('sensitive_fields', []))}")
    
    with tab3:
        st.subheader("Comparison")
        st.write(f"**Body Diff Ratio:** {attempt.get('body_diff_ratio', 'N/A')}")
        st.write(f"**Consistency:** {attempt.get('consistent')}")
    
    with tab4:
        st.subheader("Replay Command")
        curl_cmd = attempt.get("curl_command", "No curl command available")
        st.code(curl_cmd, language="bash")
        
        if st.button("Copy to Clipboard"):
            st.write("✅ Copied! (paste in terminal)")
    
    st.divider()
    
    # Reproduction steps
    st.subheader("Reproduction Steps")
    reproduction = evidence_data.get("reproduction_steps", [])
    for step in reproduction:
        st.write(step)
    
    # Export button
    if st.button("Download as JSON"):
        json_str = json.dumps(evidence_data, indent=2)
        st.download_button(
            label="Download",
            data=json_str,
            file_name=f"evidence_{verdict_id}.json",
            mime="application/json",
        )
