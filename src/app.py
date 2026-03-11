"""
Agentic Bug Hunter - Streamlit Web Dashboard

A professional, interactive web interface for the multi-agent
bug detection system built for the Infineon RDI hackathon.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.agents.orchestrator import Orchestrator
from src.models.schemas import AnalysisResult, AnalysisSummary, Severity, BugCategory
from src.reports.generator import ReportGenerator
from src.utils.helpers import read_samples_csv, get_code_context

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Agentic Bug Hunter",
    page_icon="🐛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #58a6ff, #3fb950);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        color: #8b949e;
        font-size: 1.1rem;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    .metric-card {
        background: linear-gradient(135deg, #161b22, #1f2937);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # ── Sidebar ───────────────────────────────────────────────
    with st.sidebar:
        st.image("https://img.icons8.com/nolan/96/bug.png", width=64)
        st.markdown("## ⚙️ Configuration")
        st.divider()

        analysis_mode = st.radio(
            "Analysis Mode",
            ["📁 Upload CSV", "📝 Paste Code"],
            help="Choose how to provide code for analysis",
        )

        st.divider()
        st.markdown("### Pipeline Settings")

        use_mcp = st.toggle("🔗 MCP Grounding", value=True, help="Query documentation via MCP server")
        use_severity = st.toggle("⚠️ Severity Classification", value=True, help="Classify bug severity")
        use_explanation = st.toggle("✏️ Explanation Refinement", value=True, help="Refine bug explanations")

        st.divider()
        st.markdown(
            """
            <div style='text-align:center; color:#484f58; font-size:12px'>
                <p>Agentic Bug Hunter v1.0</p>
                <p>Powered by Gemini + MCP</p>
                <p>Infineon Hackathon 2025</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Header ────────────────────────────────────────────────
    st.markdown('<p class="main-header">🐛 Agentic Bug Hunter</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Multi-Agent AI System for Detecting Semantic Bugs in Infineon RDI Test Code</p>',
        unsafe_allow_html=True,
    )

    # ── Tabs ──────────────────────────────────────────────────
    tab_analyze, tab_results, tab_pipeline, tab_about = st.tabs(
        ["🔍 Analyze", "📊 Results", "🔄 Pipeline View", "ℹ️ About"]
    )

    # ════════════════════════════════════════════════════════════
    #  TAB 1: ANALYZE
    # ════════════════════════════════════════════════════════════
    with tab_analyze:
        if analysis_mode == "📁 Upload CSV":
            _render_csv_upload(use_mcp, use_severity, use_explanation)
        else:
            _render_code_paste(use_mcp, use_severity, use_explanation)

    # ════════════════════════════════════════════════════════════
    #  TAB 2: RESULTS
    # ════════════════════════════════════════════════════════════
    with tab_results:
        _render_results()

    # ════════════════════════════════════════════════════════════
    #  TAB 3: PIPELINE VIEW
    # ════════════════════════════════════════════════════════════
    with tab_pipeline:
        _render_pipeline()

    # ════════════════════════════════════════════════════════════
    #  TAB 4: ABOUT
    # ════════════════════════════════════════════════════════════
    with tab_about:
        _render_about()


# ──────────────────────────────────────────────────────────────
#  CSV Upload Mode
# ──────────────────────────────────────────────────────────────
def _render_csv_upload(use_mcp: bool, use_severity: bool, use_explanation: bool):
    st.markdown("### 📁 Upload Code Samples CSV")
    st.info("Upload a CSV file with columns: **ID**, **Code**")

    uploaded = st.file_uploader(
        "Choose a samples CSV file",
        type=["csv"],
        help="CSV must have 'ID' and 'Code' columns",
    )

    if uploaded:
        # Parse CSV
        content = uploaded.getvalue().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        samples = [{"ID": row["ID"], "Code": row["Code"]} for row in reader]

        st.success(f"Loaded **{len(samples)}** code samples")

        # Preview
        with st.expander("👀 Preview Samples", expanded=False):
            for s in samples[:3]:
                st.markdown(f"**Sample {s['ID']}**")
                st.code(s["Code"][:500], language="cpp")

        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            _run_analysis(samples, use_mcp, use_severity, use_explanation)


# ──────────────────────────────────────────────────────────────
#  Code Paste Mode
# ──────────────────────────────────────────────────────────────
def _render_code_paste(use_mcp: bool, use_severity: bool, use_explanation: bool):
    st.markdown("### 📝 Paste C++ Code for Analysis")

    sample_id = st.text_input("Sample ID", value="SAMPLE_001", help="Identifier for this code sample")

    code = st.text_area(
        "C++ Code",
        height=400,
        placeholder="Paste your Infineon RDI C++ test code here...",
        help="The code will be analyzed for semantic bugs",
    )

    if code and st.button("🚀 Analyze Code", type="primary", use_container_width=True):
        samples = [{"ID": sample_id, "Code": code}]
        _run_analysis(samples, use_mcp, use_severity, use_explanation)


# ──────────────────────────────────────────────────────────────
#  Run Analysis
# ──────────────────────────────────────────────────────────────
def _run_analysis(
    samples: list[dict],
    use_mcp: bool,
    use_severity: bool,
    use_explanation: bool,
):
    """Run the multi-agent analysis pipeline with progress tracking."""

    orchestrator = Orchestrator()

    # Apply user's pipeline preferences
    orchestrator.mcp_enabled = use_mcp
    orchestrator.severity_enabled = use_severity
    orchestrator.explanation_enabled = use_explanation

    progress_bar = st.progress(0, text="Initializing pipeline...")
    status_text = st.empty()

    def update_progress(text: str, pct: float):
        progress_bar.progress(min(pct, 1.0), text=text)
        status_text.text(text)

    results, summary = orchestrator.analyze_batch(samples, progress_callback=update_progress)

    progress_bar.progress(1.0, text="✅ Analysis complete!")

    # Store in session state
    st.session_state["results"] = results
    st.session_state["summary"] = summary

    # Generate reports
    generator = ReportGenerator()
    outputs = generator.generate_all(results, summary)
    st.session_state["report_files"] = outputs

    st.success(f"Found **{summary.total_bugs}** bugs across **{summary.total_samples}** samples!")
    st.balloons()

    # Show quick summary
    _render_summary_metrics(summary)


# ──────────────────────────────────────────────────────────────
#  Summary Metrics
# ──────────────────────────────────────────────────────────────
def _render_summary_metrics(summary: AnalysisSummary):
    """Render the summary statistics cards."""
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("📄 Samples", summary.total_samples)
    with col2:
        st.metric("🐛 Total Bugs", summary.total_bugs)
    with col3:
        st.metric("📊 Avg/Sample", f"{summary.avg_bugs_per_sample:.1f}")
    with col4:
        st.metric("🔴 Critical", summary.bugs_by_severity.get("CRITICAL", 0))
    with col5:
        st.metric("🟠 High", summary.bugs_by_severity.get("HIGH", 0))
    with col6:
        st.metric("⏱️ Time", f"{summary.processing_time_ms / 1000:.1f}s")


# ──────────────────────────────────────────────────────────────
#  Results Tab
# ──────────────────────────────────────────────────────────────
def _render_results():
    """Render the detailed results view."""
    if "results" not in st.session_state:
        st.info("Run an analysis first to see results here.")
        return

    results: list[AnalysisResult] = st.session_state["results"]
    summary: AnalysisSummary = st.session_state["summary"]

    _render_summary_metrics(summary)

    st.divider()

    # Charts
    col_sev, col_cat = st.columns(2)

    with col_sev:
        st.markdown("#### Bugs by Severity")
        if summary.bugs_by_severity:
            import pandas as pd
            sev_df = pd.DataFrame(
                list(summary.bugs_by_severity.items()),
                columns=["Severity", "Count"],
            )
            st.bar_chart(sev_df, x="Severity", y="Count", color="#58a6ff")

    with col_cat:
        st.markdown("#### Bugs by Category")
        if summary.bugs_by_category:
            import pandas as pd
            cat_df = pd.DataFrame(
                list(summary.bugs_by_category.items()),
                columns=["Category", "Count"],
            )
            st.bar_chart(cat_df, x="Category", y="Count", color="#3fb950")

    st.divider()

    # Detailed bug table
    st.markdown("### 📋 Detailed Bug Reports")

    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        sev_filter = st.multiselect(
            "Filter by Severity",
            options=[s.value for s in Severity],
            default=[s.value for s in Severity],
        )
    with fcol2:
        cat_filter = st.multiselect(
            "Filter by Category",
            options=[c.value for c in BugCategory],
            default=[c.value for c in BugCategory],
        )
    with fcol3:
        sample_ids = list({r.sample_id for r in results})
        id_filter = st.multiselect(
            "Filter by Sample ID",
            options=sample_ids,
            default=sample_ids,
        )

    # Build filtered bug list
    for result in results:
        if result.sample_id not in id_filter:
            continue
        for bug in result.bugs:
            if bug.severity.value not in sev_filter:
                continue
            if bug.category.value not in cat_filter:
                continue

            severity_emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
            }
            emoji = severity_emoji.get(bug.severity.value, "⚪")

            with st.expander(
                f"{emoji} **{bug.id}** | Line {bug.bug_line} | {bug.severity.value} | {bug.category.value}"
            ):
                st.markdown(f"**Explanation:** {bug.explanation}")
                st.code(bug.code_line, language="cpp")

                if bug.docs_context:
                    st.markdown("**📚 Documentation Context:**")
                    st.caption(bug.docs_context[:300])

                mcol1, mcol2, mcol3 = st.columns(3)
                with mcol1:
                    st.metric("Confidence", f"{bug.confidence:.0%}")
                with mcol2:
                    st.metric("Line", bug.bug_line)
                with mcol3:
                    st.metric("Severity", bug.severity.value)

                # Show code context
                if result.code:
                    st.markdown("**📄 Code Context:**")
                    ctx = get_code_context(result.code, bug.bug_line, context_lines=5)
                    st.code(ctx, language="text")

    # Download buttons
    st.divider()
    st.markdown("### 📥 Download Reports")

    report_files = st.session_state.get("report_files", {})
    dcol1, dcol2, dcol3 = st.columns(3)

    for col, (fmt, path) in zip([dcol1, dcol2, dcol3], report_files.items()):
        with col:
            if Path(path).exists():
                with open(path, "rb") as f:
                    st.download_button(
                        f"⬇️ Download {fmt.upper()}",
                        data=f.read(),
                        file_name=Path(path).name,
                        mime="text/csv" if fmt == "csv" else "application/json" if fmt == "json" else "text/html",
                        use_container_width=True,
                    )


# ──────────────────────────────────────────────────────────────
#  Pipeline View
# ──────────────────────────────────────────────────────────────
def _render_pipeline():
    """Render the agent pipeline visualization."""
    st.markdown("### 🔄 Multi-Agent Pipeline Architecture")

    # Pipeline diagram using columns
    st.markdown("""
    ```
    ┌─────────────────────────────────────────────────────────────────┐
    │                    AGENTIC BUG HUNTER PIPELINE                  │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │   📄 Input (samples.csv)                                        │
    │        │                                                        │
    │        ▼                                                        │
    │   ┌─────────────────────────┐                                   │
    │   │   🧠 Reasoning Agent    │  Gemini 2.5 Flash                 │
    │   │   (Bug Discovery)       │  Analyzes C++ RDI code            │
    │   └──────────┬──────────────┘                                   │
    │              │ Bug Hypotheses                                    │
    │              ▼                                                   │
    │   ┌─────────────────────────┐                                   │
    │   │   📚 MCP Knowledge      │  Infineon MCP Server              │
    │   │   Agent (Grounding)     │  Vector similarity search         │
    │   └──────────┬──────────────┘                                   │
    │              │ Documentation Context                             │
    │              ▼                                                   │
    │   ┌─────────────────────────┐                                   │
    │   │   ⚠️  Severity Agent    │  Gemini Classification            │
    │   │   (Risk Assessment)     │  CRITICAL/HIGH/MEDIUM/LOW         │
    │   └──────────┬──────────────┘                                   │
    │              │ Severity + Justification                          │
    │              ▼                                                   │
    │   ┌─────────────────────────┐                                   │
    │   │   ✏️  Explanation Agent  │  Gemini Refinement                │
    │   │   (Report Refinement)   │  Dataset-style output             │
    │   └──────────┬──────────────┘                                   │
    │              │                                                   │
    │              ▼                                                   │
    │   📊 Output (CSV + HTML + JSON Reports)                         │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    ```
    """)

    # Agent trace
    if "results" in st.session_state:
        st.divider()
        st.markdown("### 📜 Agent Execution Trace")

        results: list[AnalysisResult] = st.session_state["results"]
        for result in results:
            with st.expander(f"🔬 Sample: {result.sample_id} — {len(result.agent_trace)} agent events"):
                for i, event in enumerate(result.agent_trace):
                    status_icon = "✅" if event.status == "success" else "❌"
                    st.markdown(
                        f"**{i + 1}.** {status_icon} `{event.agent_name}` — "
                        f"{event.duration_ms:.0f}ms — {event.output_summary[:100]}"
                    )


# ──────────────────────────────────────────────────────────────
#  About Tab
# ──────────────────────────────────────────────────────────────
def _render_about():
    """Render the about page."""
    st.markdown("""
    ### About Agentic Bug Hunter

    **Agentic Bug Hunter** is a multi-agent AI system designed to automatically detect
    semantic bugs in Infineon's RDI (Reliability, Durability, and Integration) C++ test programs.

    #### 🏆 Hackathon Context
    Developed for the **Infineon Technologies Agentic Bug Hunter Track**, this system uses
    a pipeline of specialized AI agents to discover, validate, classify, and explain bugs
    in semiconductor testing code.

    #### 🧩 Agent Architecture

    | Agent | Role | Technology |
    |-------|------|------------|
    | **Reasoning Agent** | Bug discovery via LLM analysis | Google Gemini 2.5 Flash |
    | **MCP Knowledge Agent** | Documentation grounding | Infineon MCP Server (FastMCP) |
    | **Severity Agent** | Risk classification | Gemini + embedded systems knowledge |
    | **Explanation Agent** | Report refinement | Gemini with dataset-style formatting |

    #### 🛠️ Technology Stack

    - **LLM**: Google Gemini 2.5 Flash
    - **MCP Server**: FastMCP with LlamaIndex vector store + BAAI/bge-base-en-v1.5 embeddings
    - **Framework**: Python 3.11+ with Pydantic v2
    - **Dashboard**: Streamlit
    - **Reports**: CSV, HTML, JSON

    #### 📈 Key Features
    - Multi-agent pipeline with clear separation of concerns
    - Real-time progress tracking with agent execution traces
    - Severity classification (Critical / High / Medium / Low)
    - Bug categorization (API Misuse, Logic Error, Resource Management, etc.)
    - Interactive code viewer showing bugs inline with context
    - Multi-format report generation (CSV + HTML + JSON)
    - Professional HTML reports with charts and statistics
    - MCP-based documentation grounding for verified explanations
    """)


if __name__ == "__main__":
    main()
