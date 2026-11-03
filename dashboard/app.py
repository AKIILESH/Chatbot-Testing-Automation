import os
import sys
import json
import asyncio
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.test_runner import TestRunner
from app.regression import RegressionDetector
from app.schemas import TestSuiteRun

# Page Configuration
st.set_page_config(
    page_title="LLM Quality Tester — Atomberg AI Automation",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme & professional styling
st.markdown(
    """
    <style>
    /* Global modern dark palette */
    .stApp {
        background-color: #0b0f17;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Top banner */
    .qa-header {
        background: linear-gradient(135deg, #131b2e 0%, #17223b 100%);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .qa-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .qa-subtitle {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 4px;
        margin-bottom: 0;
    }
    
    /* Metric Cards */
    .metric-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 16px 20px;
        transition: border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: #374151;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .metric-val {
        font-size: 1.75rem;
        font-weight: 700;
        color: #f1f5f9;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 4px;
    }
    
    /* Status Pills */
    .status-pill-pass {
        background-color: #064e3b;
        color: #34d399;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .status-pill-fail {
        background-color: #7f1d1d;
        color: #f87171;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Code block container */
    .stCodeBlock {
        border-radius: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_services():
    runner = TestRunner()
    regression_detector = RegressionDetector(test_runner=runner)
    return runner, regression_detector


runner, regression_detector = get_services()


# Top Navigation / Header
st.markdown(
    """
    <div class="qa-header">
        <div>
            <h1 class="qa-title">🛡️ LLM Quality Tester <span style="font-size:0.8rem; background:#1e293b; color:#38bdf8; padding:3px 8px; border-radius:6px; border:1px solid #334155;">Atomberg Aura QA</span></h1>
            <p class="qa-subtitle">Automated Evaluation, Hallucination Detection, Prompt Injection Defense & Regression Testing</p>
        </div>
        <div style="text-align: right;">
            <span style="font-size:0.8rem; color:#94a3b8;">Target App: <strong>Atomberg Smart Home IoT Assistant</strong></span><br/>
            <span style="font-size:0.75rem; color:#64748b;">Framework: DeepEval + Custom Deterministic Grounding & SLA Guard</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar controls
with st.sidebar:
    st.markdown("### ⚙️ Test Suite Controls")
    
    execution_mode = st.radio(
        "Execution Provider",
        ["Offline Mock Engine (Deterministic)", "Live LLM API (OpenAI-compatible)"],
        index=0,
        help="Mock engine requires zero API keys and produces deterministic, instant evaluation results.",
    )
    use_mock = "Mock" in execution_mode
    
    model_name = "gpt-4o-mini"
    if not use_mock:
        model_name = st.text_input("Model Identifier", value="gpt-4o-mini")
        api_key_input = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        if api_key_input:
            os.environ["OPENAI_API_KEY"] = api_key_input

    # Category Selector
    all_categories = [
        "All Categories",
        "smart_home_factual",
        "general_factual",
        "context_grounded",
        "hallucination_detection",
        "multi_turn_context",
        "security_prompt_injection",
        "security_pii_leakage",
        "security_unauthorized_device_control",
        "refusal_behavior",
        "incorrect_answer_scenario",
    ]
    selected_cat = st.selectbox("Category Filter", all_categories, index=0)

    # Flaw injection toggle for testing the tester
    simulate_flaws = st.checkbox(
        "Simulate Flaw Injection (Negative QA)",
        value=False,
        help="Intentionally triggers flawed responses on trap questions to verify hallucination and safety detection alerts.",
    )

    st.markdown("---")
    st.markdown("### 📊 Test Dataset")
    try:
        cases = runner.load_test_cases()
        st.caption(f"Loaded **{len(cases)}** verified golden test cases from `data/golden_dataset.json`.")
    except Exception as e:
        st.error(f"Error loading dataset: {e}")

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size: 0.75rem; color: #64748b; line-height: 1.4;">
            <strong>AI Quality Engineer Application</strong><br/>
            Atomberg Technologies<br/>
            Evaluation Metrics: DeepEval, Token Containment, Semantic Sim, Regex Guardrails.
        </div>
        """,
        unsafe_allow_html=True,
    )


# Tabs for Main View
tab_overview, tab_execution, tab_security, tab_regression = st.tabs([
    "📈 Overview & Metrics",
    "🚀 Test Suite Execution",
    "🔒 Security & Jailbreak Defense",
    "📉 Regression Analysis",
])


# Helper function to run tests
def execute_test_run(cat_filter, mock_mode, model_id, sim_flaws):
    categories = None if cat_filter == "All Categories" else [cat_filter]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    run_result = loop.run_until_complete(
        runner.run_suite(
            categories=categories,
            use_mock=mock_mode,
            model=model_id,
            simulate_flaws=sim_flaws,
        )
    )
    loop.close()
    return run_result


# Fetch latest run or auto-initialize one if none exists
latest_run = runner.get_latest_run()
if not latest_run:
    # Run initial baseline test suite silently
    latest_run = execute_test_run("All Categories", True, "mock-aura", False)


# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW & METRICS
# -----------------------------------------------------------------------------
with tab_overview:
    # Key Metric Cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Tests</div>
                <div class="metric-val">{latest_run.total_tests}</div>
                <div class="metric-sub">Run: {latest_run.run_id[:16]}...</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 3px solid #10b981;">
                <div class="metric-label">Passed Tests</div>
                <div class="metric-val" style="color: #34d399;">{latest_run.passed_tests}</div>
                <div class="metric-sub">Passing criteria met</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        fail_color = "#f87171" if latest_run.failed_tests > 0 else "#94a3b8"
        border_color = "#ef4444" if latest_run.failed_tests > 0 else "#1f2937"
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 3px solid {border_color};">
                <div class="metric-label">Failed Tests</div>
                <div class="metric-val" style="color: {fail_color};">{latest_run.failed_tests}</div>
                <div class="metric-sub">Flaws / breaches flagged</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Pass Rate</div>
                <div class="metric-val" style="color: #38bdf8;">{latest_run.pass_rate}%</div>
                <div class="metric-sub">Target SLA: ≥ 90%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Avg Latency</div>
                <div class="metric-val">{latest_run.avg_latency_ms:.0f} <span style="font-size:0.9rem; color:#94a3b8;">ms</span></div>
                <div class="metric-sub">SLA Threshold: 3000ms</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c6:
        halluc_color = "#f87171" if latest_run.hallucination_rate > 0 else "#34d399"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Hallucination</div>
                <div class="metric-val" style="color: {halluc_color};">{latest_run.hallucination_rate}%</div>
                <div class="metric-sub">Ungrounded rate</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    # Charts Row
    ch1, ch2 = st.columns(2)
    
    with ch1:
        st.markdown("##### 📊 Results by Test Category")
        df_results = pd.DataFrame([
            {
                "Category": r.category.replace("_", " ").title(),
                "Status": "Passed" if r.passed else "Failed",
                "Count": 1,
            }
            for r in latest_run.results
        ])
        if not df_results.empty:
            cat_summary = df_results.groupby(["Category", "Status"]).count().reset_index()
            fig_cat = px.bar(
                cat_summary,
                x="Category",
                y="Count",
                color="Status",
                color_discrete_map={"Passed": "#10b981", "Failed": "#ef4444"},
                barmode="stack",
                height=320,
            )
            fig_cat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#1e293b"),
                margin=dict(l=20, r=20, t=20, b=50),
            )
            st.plotly_chart(fig_cat, use_container_width=True)

    with ch2:
        st.markdown("##### ⏱️ Response Latency Distribution (ms)")
        lat_df = pd.DataFrame([
            {
                "Test ID": r.test_id,
                "Latency (ms)": r.latency_ms,
                "Passed": "Pass" if r.passed else "Fail",
            }
            for r in latest_run.results
        ])
        if not lat_df.empty:
            fig_lat = px.bar(
                lat_df,
                x="Test ID",
                y="Latency (ms)",
                color="Passed",
                color_discrete_map={"Pass": "#38bdf8", "Fail": "#f43f5e"},
                height=320,
            )
            fig_lat.add_hline(y=2500, line_dash="dash", line_color="#f59e0b", annotation_text="Standard SLA (2500ms)")
            fig_lat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#1e293b"),
                margin=dict(l=20, r=20, t=20, b=50),
            )
            st.plotly_chart(fig_lat, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 2: TEST SUITE EXECUTION
# -----------------------------------------------------------------------------
with tab_execution:
    st.markdown("##### 🚀 Test Suite Execution Controller")
    
    col_run_btn, col_info = st.columns([1, 3])
    with col_run_btn:
        run_now = st.button("▶️ Run Test Suite", type="primary", use_container_width=True)
    with col_info:
        st.info(f"Target: **{selected_cat}** | Mode: **{'Offline Mock' if use_mock else f'Live API ({model_name})'}** | Flaw Simulation: **{simulate_flaws}**")

    if run_now:
        with st.spinner("Executing automated test suite and evaluating responses..."):
            progress_bar = st.progress(0)
            for p in range(1, 80, 20):
                progress_bar.progress(p)
            new_run = execute_test_run(selected_cat, use_mock, model_name, simulate_flaws)
            progress_bar.progress(100)
            st.success(f"Execution complete! Run ID: `{new_run.run_id}` | Pass Rate: **{new_run.pass_rate}%**")
            st.rerun()

    st.markdown("---")
    st.markdown("##### 📋 Test Execution Results")

    # Filter controls for table
    filter_col1, filter_col2 = st.columns([1, 2])
    with filter_col1:
        status_filter = st.selectbox("Filter Status", ["All", "Passed Only", "Failed Only"], index=0)
    with filter_col2:
        search_term = st.text_input("Search Prompt or Name", placeholder="e.g. sleep mode, door lock, injection...")

    display_results = latest_run.results
    if status_filter == "Passed Only":
        display_results = [r for r in display_results if r.passed]
    elif status_filter == "Failed Only":
        display_results = [r for r in display_results if not r.passed]

    if search_term:
        term = search_term.lower()
        display_results = [
            r for r in display_results
            if term in r.prompt.lower() or term in r.name.lower() or term in r.category.lower()
        ]

    # Render results in clean accordion list
    st.markdown(f"Displaying **{len(display_results)}** of **{latest_run.total_tests}** test results:")
    for res in display_results:
        status_badge = "✅ PASSED" if res.passed else "❌ FAILED"
        halluc_badge = " [⚠️ HALLUCINATED]" if res.is_hallucinated else ""
        sec_badge = " [🚨 SECURITY ALERT]" if res.security_incident_detected else ""
        
        with st.expander(f"{res.test_id} — {res.name} | {status_badge}{halluc_badge}{sec_badge} ({res.latency_ms:.1f}ms)"):
            c_det1, c_det2 = st.columns([1, 1])
            with c_det1:
                st.markdown("**Prompt:**")
                st.code(res.prompt, language=None)
                if res.context:
                    st.markdown("**Context / Conversation History:**")
                    st.code(res.context, language=None)
                st.markdown("**Expected Golden Answer / Policy:**")
                st.code(res.expected_answer, language=None)
            
            with c_det2:
                st.markdown("**Actual LLM Response:**")
                st.code(res.actual_response, language=None)
                
                st.markdown("**Metric Scores & Reasonings:**")
                for m_name, m_val in res.metrics.items():
                    m_icon = "🟢" if m_val.passed else "🔴"
                    st.markdown(f"- {m_icon} **{m_name}**: `{m_val.score:.2f}` (Threshold: {m_val.threshold}) — *{m_val.reasoning}*")


# -----------------------------------------------------------------------------
# TAB 3: SECURITY & JAILBREAK DEFENSE
# -----------------------------------------------------------------------------
with tab_security:
    st.markdown("##### 🔒 Adversarial Security & Defensive Evaluation")
    st.caption("Validates defensive posture against prompt injections, DAN jailbreaks, credential/PII leaks, and unauthorized IoT physical actuators.")

    security_results = [r for r in latest_run.results if "security" in r.category or "refusal" in r.category or r.security_sensitive]

    sec_c1, sec_c2, sec_c3 = st.columns(3)
    sec_passed = sum(1 for r in security_results if r.passed)
    sec_breaches = len(security_results) - sec_passed
    sec_pass_rate = round((sec_passed / len(security_results)) * 100.0, 1) if security_results else 100.0

    with sec_c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Security Test Scenarios</div>
                <div class="metric-val">{len(security_results)}</div>
                <div class="metric-sub">Adversarial & PII boundaries</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sec_c2:
        sec_stat_color = "#34d399" if sec_breaches == 0 else "#f87171"
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 3px solid {sec_stat_color};">
                <div class="metric-label">Defensive Pass Rate</div>
                <div class="metric-val" style="color: {sec_stat_color};">{sec_pass_rate}%</div>
                <div class="metric-sub">Zero-tolerance for PII/bypasses</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sec_c3:
        b_color = "#f87171" if sec_breaches > 0 else "#94a3b8"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Security Breaches Detected</div>
                <div class="metric-val" style="color: {b_color};">{sec_breaches}</div>
                <div class="metric-sub">Compromised safety boundaries</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    sec_table_data = []
    for r in security_results:
        sec_table_data.append({
            "Test ID": r.test_id,
            "Attack Vector": r.category.replace("security_", "").replace("_", " ").title(),
            "Scenario": r.name,
            "Defense Upheld": "🛡️ Defended (Pass)" if r.passed else "🚨 Breached (Fail)",
            "Guardrail Diagnostic": r.metrics.get("security_guardrail", r.metrics.get("answer_correctness")).reasoning if r.metrics else "Evaluated",
        })
    st.dataframe(pd.DataFrame(sec_table_data), use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# TAB 4: REGRESSION ANALYSIS
# -----------------------------------------------------------------------------
with tab_regression:
    st.markdown("##### 📉 Automated Regression Detection")
    st.caption("Compares current test execution with previous baseline to proactively detect quality degradation and latency increases.")

    reg_report = regression_detector.evaluate_latest_regression()

    if not reg_report.has_comparison:
        st.warning(f"ℹ️ {reg_report.status_summary}")
        st.info("Execute another test run from the sidebar or Test Suite tab to perform an automated regression diff.")
    else:
        # Comparison Metrics
        r_c1, r_c2, r_c3, r_c4 = st.columns(4)
        with r_c1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Current Pass Rate</div>
                    <div class="metric-val">{reg_report.current_pass_rate}%</div>
                    <div class="metric-sub">Run: {reg_report.current_run_id[:14]}...</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r_c2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Previous Pass Rate</div>
                    <div class="metric-val">{reg_report.previous_pass_rate}%</div>
                    <div class="metric-sub">Run: {reg_report.previous_run_id[:14]}...</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r_c3:
            delta = reg_report.pass_rate_delta or 0.0
            delta_color = "#34d399" if delta >= 0 else "#f87171"
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 3px solid {delta_color};">
                    <div class="metric-label">Pass Rate Delta</div>
                    <div class="metric-val" style="color: {delta_color};">{delta:+0.2f}%</div>
                    <div class="metric-sub">Quality difference</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r_c4:
            lat_delta = reg_report.latency_delta_ms or 0.0
            lat_color = "#f87171" if reg_report.latency_increased else "#38bdf8"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Latency Delta</div>
                    <div class="metric-val" style="color: {lat_color};">{lat_delta:+0.1f} ms</div>
                    <div class="metric-sub">Response timing delta</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br/>", unsafe_allow_html=True)

        if reg_report.quality_degraded:
            st.error(f"⚠️ **Regression Alert:** {reg_report.status_summary}")
        else:
            st.success(f"✅ **Regression Check Passed:** {reg_report.status_summary}")

        if reg_report.newly_failing_tests:
            st.markdown("##### 🚨 Newly Failing Tests (Broken in Current Run):")
            for nf in reg_report.newly_failing_tests:
                st.markdown(f"- 🔴 `{nf}`")

        if reg_report.newly_passing_tests:
            st.markdown("##### 🎉 Newly Passing Tests (Fixed in Current Run):")
            for np_test in reg_report.newly_passing_tests:
                st.markdown(f"- 🟢 `{np_test}`")
