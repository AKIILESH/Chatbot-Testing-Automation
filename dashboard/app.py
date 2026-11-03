import os
import sys
import json
import asyncio
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ensure project root is first in sys.path and resolve any 'app' package namespace collisions
root_dir = Path(__file__).resolve().parent.parent
root_str = str(root_dir)
if sys.path[0] != root_str:
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)

if "app" in sys.modules and not hasattr(sys.modules["app"], "__path__"):
    del sys.modules["app"]

from app.test_runner import TestRunner
from app.procurement_data import procurement_store, format_inr
from app.chatbot import ProcurementChatbot
from app.schemas import TestSuiteRun

# Page Configuration
st.set_page_config(
    page_title="ProcureQA — LLM Test Automation Framework",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme & professional styling
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0c1017;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    .procure-header {
        background: linear-gradient(135deg, #111a2e 0%, #172642 100%);
        border: 1px solid #1e2e4a;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .procure-title {
        font-size: 1.55rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .procure-subtitle {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-top: 4px;
        margin-bottom: 0;
    }
    
    .metric-card {
        background-color: #121824;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px 20px;
        transition: border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: #334155;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f1f5f9;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_services():
    runner = TestRunner()
    bot = ProcurementChatbot()
    return runner, bot


runner, chatbot = get_services()

# Top Header
st.markdown(
    """
    <div class="procure-header">
        <div>
            <h1 class="procure-title">📦 ProcureQA <span style="font-size:0.8rem; background:#1e293b; color:#38bdf8; padding:3px 9px; border-radius:6px; border:1px solid #334155;">Enterprise Edition</span></h1>
            <p class="procure-subtitle">Automated LLM Testing for Procurement: Correctness, Hallucination Traps, Security Defense & Latency SLAs</p>
        </div>
        <div style="text-align: right;">
            <span style="font-size:0.82rem; color:#94a3b8;">Domain: <strong>Enterprise Procurement & Purchasing</strong></span><br/>
            <span style="font-size:0.75rem; color:#64748b;">Framework: DeepEval + Deterministic Grounded Assertions</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar Controls
with st.sidebar:
    st.markdown("### ⚙️ Automation Controls")
    
    execution_mode = st.radio(
        "Execution Provider",
        ["Deterministic Mock Engine (Offline)", "Live OpenAI LLM API"],
        index=0,
        help="Deterministic mock engine runs offline with zero external API keys and guarantees reproducible testing.",
    )
    use_mock = "Mock" in execution_mode
    
    model_name = "gpt-4o-mini"
    if not use_mock:
        model_name = st.text_input("Model ID", value="gpt-4o-mini")
        api_key_input = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        if api_key_input:
            os.environ["OPENAI_API_KEY"] = api_key_input

    categories = [
        "All Categories",
        "correctness",
        "hallucination",
        "security",
        "api_testing",
        "performance",
    ]
    selected_cat = st.selectbox("Category Filter", categories, index=0)

    simulate_flaw = st.checkbox(
        "Simulate Flaw Injection (Negative QA)",
        value=False,
        help="Simulates hallucinated confirmations on nonexistent purchase orders to test the framework's failure detection.",
    )

    st.markdown("---")
    st.markdown("### 📊 Golden Dataset")
    total_golden = len(procurement_store.test_cases)
    st.caption(f"Loaded **{total_golden}** test cases from `data/procurement.json`.")
    st.caption(f"• **{len(procurement_store.purchase_requisitions)}** Purchase Requisitions\n• **{len(procurement_store.purchase_orders)}** Purchase Orders\n• **{len(procurement_store.vendors)}** Approved Vendors\n• **{len(procurement_store.policies)}** Procurement Policies")


# Helper function to run tests
def execute_suite(cat_filter, mock_mode, model_id, sim_flaw):
    cat_list = None if cat_filter == "All Categories" else [cat_filter]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    run_res = loop.run_until_complete(
        runner.run_suite(
            categories=cat_list,
            use_mock=mock_mode,
            model=model_id,
            simulate_flaw=sim_flaw,
        )
    )
    loop.close()
    return run_res


# Fetch or execute initial run
latest_run = runner.get_latest_run()
if not latest_run:
    latest_run = execute_suite("All Categories", True, "mock-procure", False)


# Tabs
tab_overview, tab_execution, tab_security, tab_explorer, tab_live_chat = st.tabs([
    "📈 Overview & Metrics",
    "🚀 Test Suite Execution",
    "🔒 Security & Policy Defense",
    "🗂️ Procurement Data Explorer",
    "💬 Interactive Chatbot",
])


# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW & METRICS
# -----------------------------------------------------------------------------
with tab_overview:
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
        fail_c = "#f87171" if latest_run.failed_tests > 0 else "#94a3b8"
        border_c = "#ef4444" if latest_run.failed_tests > 0 else "#1e293b"
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 3px solid {border_c};">
                <div class="metric-label">Failed Tests</div>
                <div class="metric-val" style="color: {fail_c};">{latest_run.failed_tests}</div>
                <div class="metric-sub">Issues flagged</div>
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
                <div class="metric-sub">Target SLA: ≥ 95%</div>
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
                <div class="metric-sub">SLA Threshold: 2500ms</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c6:
        h_color = "#f87171" if latest_run.hallucination_rate > 0 else "#34d399"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Hallucination</div>
                <div class="metric-val" style="color: {h_color};">{latest_run.hallucination_rate}%</div>
                <div class="metric-sub">Unverified claims</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    # Charts
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("##### 📊 Results Breakdown by Test Category")
        df_res = pd.DataFrame([
            {
                "Category": r.category.replace("_", " ").title(),
                "Status": "Passed" if r.passed else "Failed",
                "Count": 1,
            }
            for r in latest_run.results
        ])
        if not df_res.empty:
            summary_cat = df_res.groupby(["Category", "Status"]).count().reset_index()
            fig_cat = px.bar(
                summary_cat,
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
            st.plotly_chart(fig_cat, width="stretch")

    with ch2:
        st.markdown("##### ⏱️ Response Latency Distribution (ms)")
        df_lat = pd.DataFrame([
            {
                "Test ID": r.test_id,
                "Latency (ms)": r.latency_ms,
                "Status": "Pass" if r.passed else "Fail",
            }
            for r in latest_run.results
        ])
        if not df_lat.empty:
            fig_lat = px.bar(
                df_lat,
                x="Test ID",
                y="Latency (ms)",
                color="Status",
                color_discrete_map={"Pass": "#38bdf8", "Fail": "#f43f5e"},
                height=320,
            )
            fig_lat.add_hline(y=2000, line_dash="dash", line_color="#f59e0b", annotation_text="Standard SLA (2000ms)")
            fig_lat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#1e293b"),
                margin=dict(l=20, r=20, t=20, b=50),
            )
            st.plotly_chart(fig_lat, width="stretch")


# -----------------------------------------------------------------------------
# TAB 2: TEST SUITE EXECUTION
# -----------------------------------------------------------------------------
with tab_execution:
    st.markdown("##### 🚀 Test Suite Execution Controller")
    c_btn, c_banner = st.columns([1, 3])
    with c_btn:
        run_now = st.button("▶️ Run Test Suite", type="primary", width="stretch")
    with c_banner:
        st.info(f"Target: **{selected_cat}** | Mode: **{'Deterministic Mock' if use_mock else f'Live API ({model_name})'}** | Flaw Simulation: **{simulate_flaw}**")

    if run_now:
        with st.spinner("Executing procurement test suite and evaluating responses..."):
            pbar = st.progress(0)
            for step in range(20, 90, 20):
                pbar.progress(step)
            new_run = execute_suite(selected_cat, use_mock, model_name, simulate_flaw)
            pbar.progress(100)
            st.success(f"Executed Run `{new_run.run_id}` | Pass Rate: **{new_run.pass_rate}%** ({new_run.passed_tests}/{new_run.total_tests})")
            st.rerun()

    st.markdown("---")
    st.markdown("##### 📋 Execution Results")

    col_flt1, col_flt2 = st.columns([1, 2])
    with col_flt1:
        status_choice = st.selectbox("Status Filter", ["All", "Passed Only", "Failed Only"], index=0)
    with col_flt2:
        search_kw = st.text_input("Search Test Name / Prompt", placeholder="e.g. PR-1024, PO-2045, injection, budget...")

    filtered_results = latest_run.results
    if status_choice == "Passed Only":
        filtered_results = [r for r in filtered_results if r.passed]
    elif status_choice == "Failed Only":
        filtered_results = [r for r in filtered_results if not r.passed]

    if search_kw:
        skw = search_kw.lower()
        filtered_results = [
            r for r in filtered_results
            if skw in r.name.lower() or skw in r.prompt.lower() or skw in r.category.lower()
        ]

    st.markdown(f"Showing **{len(filtered_results)}** of **{latest_run.total_tests}** test results:")

    for res in filtered_results:
        badge = "✅ PASSED" if res.passed else "❌ FAILED"
        halluc_badge = " [⚠️ HALLUCINATED]" if res.is_hallucinated else ""
        sec_badge = " [🚨 SECURITY ALERT]" if res.security_incident_detected else ""

        with st.expander(f"{res.test_id} — {res.name} | {badge}{halluc_badge}{sec_badge} ({res.latency_ms:.1f}ms)"):
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("**User Query / Prompt:**")
                st.code(res.prompt, language=None)
                st.markdown("**Expected Answer / Policy Rule:**")
                st.code(res.expected_answer, language=None)
            with c_right:
                st.markdown("**Chatbot Actual Response:**")
                st.code(res.actual_response, language=None)
                st.markdown("**Evaluation Breakdown:**")
                for m_key, m_obj in res.metrics.items():
                    m_icon = "🟢" if m_obj.passed else "🔴"
                    st.markdown(f"- {m_icon} **{m_key}**: `{m_obj.score:.2f}` (Threshold: {m_obj.threshold}) — *{m_obj.reasoning}*")


# -----------------------------------------------------------------------------
# TAB 3: SECURITY & COMPLIANCE DEFENSE
# -----------------------------------------------------------------------------
with tab_security:
    st.markdown("##### 🔒 Prompt Injection, Jailbreak & Procurement Policy Defense")
    st.caption("Validates defensive posture against attempts to extract system prompts, bypass approval thresholds, leak confidential bidding margins, or manipulate database records.")

    sec_cases = [r for r in latest_run.results if r.category == "security" or r.security_sensitive]
    sec_passed = sum(1 for r in sec_cases if r.passed)
    sec_breaches = len(sec_cases) - sec_passed
    sec_rate = round((sec_passed / len(sec_cases)) * 100.0, 1) if sec_cases else 100.0

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Security Test Scenarios</div>
                <div class="metric-val">{len(sec_cases)}</div>
                <div class="metric-sub">Adversarial test cases</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sc2:
        sec_color = "#34d399" if sec_breaches == 0 else "#f87171"
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 3px solid {sec_color};">
                <div class="metric-label">Defensive Pass Rate</div>
                <div class="metric-val" style="color: {sec_color};">{sec_rate}%</div>
                <div class="metric-sub">Zero tolerance for bypasses</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sc3:
        b_c = "#f87171" if sec_breaches > 0 else "#94a3b8"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Security Breaches</div>
                <div class="metric-val" style="color: {b_c};">{sec_breaches}</div>
                <div class="metric-sub">Vulnerabilities detected</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    sec_data = []
    for r in sec_cases:
        sec_data.append({
            "Test ID": r.test_id,
            "Attack Vector": r.name,
            "Prompt Injection Payload": r.prompt[:80] + ("..." if len(r.prompt) > 80 else ""),
            "Defense Status": "🛡️ Defended (Passed)" if r.passed else "🚨 Breached (Failed)",
            "Guardrail Evaluation": r.metrics.get("security_guardrail", r.metrics.get("answer_correctness")).reasoning if r.metrics else "Evaluated",
        })
    st.dataframe(pd.DataFrame(sec_data), width="stretch", hide_index=True)


# -----------------------------------------------------------------------------
# TAB 4: PROCUREMENT DATA EXPLORER
# -----------------------------------------------------------------------------
with tab_explorer:
    st.markdown("##### 🗂️ Grounded Procurement Knowledge Base")
    st.caption("Inspect the active mock procurement database containing purchase requisitions, orders, vendors, budgets, and corporate compliance policies.")

    e_tabs = st.tabs(["Purchase Requisitions", "Purchase Orders", "Approved Vendors", "Department Budgets", "Procurement Policies"])
    
    with e_tabs[0]:
        df_pr = pd.DataFrame(procurement_store.purchase_requisitions)
        df_pr["estimated_cost"] = df_pr["estimated_cost"].apply(lambda x: f"₹{format_inr(x)}")
        st.dataframe(df_pr, width="stretch", hide_index=True)

    with e_tabs[1]:
        df_po = pd.DataFrame(procurement_store.purchase_orders)
        df_po["amount"] = df_po["amount"].apply(lambda x: f"₹{format_inr(x)}")
        st.dataframe(df_po, width="stretch", hide_index=True)

    with e_tabs[2]:
        df_v = pd.DataFrame(procurement_store.vendors)
        st.dataframe(df_v, width="stretch", hide_index=True)

    with e_tabs[3]:
        budget_data = []
        for dept, b in procurement_store.budgets.items():
            budget_data.append({
                "Department": dept,
                "Allocated Budget": f"₹{format_inr(b['allocated'])}",
                "Spent Budget": f"₹{format_inr(b['spent'])}",
                "Remaining Balance": f"₹{format_inr(b['remaining'])}",
                "Utilization": f"{(b['spent']/b['allocated'])*100:.1f}%",
            })
        st.dataframe(pd.DataFrame(budget_data), width="stretch", hide_index=True)

    with e_tabs[4]:
        df_pol = pd.DataFrame(procurement_store.policies)
        st.dataframe(df_pol, width="stretch", hide_index=True)


# -----------------------------------------------------------------------------
# TAB 5: INTERACTIVE CHATBOT
# -----------------------------------------------------------------------------
with tab_live_chat:
    st.markdown("##### 💬 Test the Procurement Chatbot Live")
    st.caption("Ask questions about requisitions (PR-1024), orders (PO-2045), vendors, budgets, or test security guardrails.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hello! I am ProcureQA, your enterprise procurement assistant. Ask me about purchase requisitions, purchase orders, vendor quotations, budgets, or approval policies."}
        ]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("Ask a procurement question (e.g. 'What is the status of PR-1024?')...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Consulting procurement database..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ans, lat, sources = loop.run_until_complete(
                    chatbot.answer_query(prompt=user_query)
                )
                loop.close()
                st.markdown(ans)
                st.caption(f"⏱️ Response latency: `{lat:.1f}ms` | Sources: {', '.join(sources)}")
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
