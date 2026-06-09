"""
Dashboard page: Replay PoC.

Allows manual re-execution of evidence attempts for verification.
"""
import requests
import streamlit as st


def render_replay_page(backend_base: str, use_backend: bool):
    """Render replay PoC tab."""
    st.header("🎬 Replay PoC")
    
    if not use_backend or not backend_base:
        st.warning("Backend not configured")
        return
    
    st.write("""
    Execute a recorded evidence attempt to verify the vulnerability.
    
    This will re-run the exact request with the same authentication context
    and compare against the baseline response.
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        verdict_id = st.number_input("Verdict ID", min_value=1, step=1)
    with col2:
        attempt_label = st.text_input("Attempt Label", "attempt_1")
    
    if not st.button("Replay Evidence Attempt", type="primary"):
        return
    
    with st.spinner("Executing..."):
        try:
            resp = requests.post(
                f"{backend_base}/verdicts/{verdict_id}/replay",
                json={"attempt_label": attempt_label},
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            st.error(f"Replay failed: {str(e)}")
            return
    
    st.success("✅ Replay completed!")
    
    st.divider()
    
    # Display result
    st.subheader("Result")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status Code", result.get("response_status_code", "N/A"))
    with col2:
        st.metric(
            "Elapsed Time", 
            f"{result.get('elapsed_ms', 0)}ms"
        )
    with col3:
        st.metric(
            "Matches Baseline", 
            "✅ Yes" if result.get("status_match") else "❌ No"
        )
    
    st.divider()
    
    # Response preview
    st.subheader("Response Preview")
    
    tabs = st.tabs(["Headers", "Body (Preview)", "Full Response"])
    
    with tabs[0]:
        headers = result.get("response_headers", {})
        for key, val in headers.items():
            st.write(f"**{key}:** {val}")
    
    with tabs[1]:
        body = result.get("response_body", "")
        if len(body) > 1000:
            st.code(body[:1000] + "... (truncated)", language="json")
        else:
            st.code(body, language="json")
    
    with tabs[2]:
        st.json(result)
    
    st.divider()
    
    # Comparison with evidence
    st.subheader("Comparison with Recorded Evidence")
    
    original_response = result.get("original_response", {})
    current_status = result.get("response_status_code")
    original_status = original_response.get("status_code")
    
    if current_status == original_status:
        st.success(f"✅ Status codes match: {current_status}")
    else:
        st.warning(f"⚠️ Status code changed: {original_status} → {current_status}")
    
    # Download option
    if st.button("Download Full Result"):
        import json
        json_str = json.dumps(result, indent=2, default=str)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"replay_result_{verdict_id}.json",
            mime="application/json",
        )
