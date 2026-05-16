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
from src.models.schemas import AnalysisResult, AnalysisSummary, Severity, BugCategory, CWE_MAPPING
from src.reports.generator import ReportGenerator
from src.evaluation.benchmark import BenchmarkEvaluator
from src.utils.helpers import read_samples_csv, get_code_context

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Agentic Bug Hunter",
    page_icon="ABH",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #c9d1d9;
        margin-bottom: 0;
        letter-spacing: -0.5px;
    }
    .sub-header {
        color: #8b949e;
        font-size: 1rem;
        margin-top: -8px;
        margin-bottom: 24px;
    }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    .severity-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .sev-critical { background: #da3633; color: #fff; }
    .sev-high { background: #d29922; color: #fff; }
    .sev-medium { background: #58a6ff; color: #fff; }
    .sev-low { background: #3fb950; color: #fff; }
    .cwe-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        background: #1f6feb;
        color: #fff;
        margin-left: 6px;
    }
    .bug-line { background: rgba(218, 54, 51, 0.15); border-left: 3px solid #da3633; }
    .bug-line-high { background: rgba(210, 153, 34, 0.12); border-left: 3px solid #d29922; }
    .bug-line-medium { background: rgba(88, 166, 255, 0.10); border-left: 3px solid #58a6ff; }
    .code-line { font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; padding: 2px 8px; white-space: pre; }
    .line-num { color: #484f58; margin-right: 12px; user-select: none; min-width: 35px; display: inline-block; text-align: right; }
    .annotated-code { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px; overflow-x: auto; margin: 12px 0; }
    .dag-node { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; text-align: center; }
    .dag-arrow { color: #58a6ff; font-size: 24px; text-align: center; }
    .benchmark-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; text-align: center; }
    .benchmark-value { font-size: 2.5rem; font-weight: 700; }
    .benchmark-label { color: #8b949e; font-size: 0.85rem; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


def main():
    # ── Sidebar ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## Configuration")
        st.divider()

        analysis_mode = st.radio(
            "Analysis Mode",
            ["Upload CSV", "Paste Code"],
            help="Choose how to provide code for analysis",
        )

        st.divider()
        st.markdown("### Pipeline Settings")

        use_mcp = st.toggle("MCP Grounding", value=True, help="Query documentation via MCP server")
        use_severity = st.toggle("Severity Classification", value=True, help="Classify bug severity")
        use_explanation = st.toggle("Explanation Refinement", value=True, help="Refine bug explanations")
        demo_mode = st.toggle("Demo Mode (Cache Only)", value=False, help="Use cached results — zero API calls")

        st.divider()
        st.markdown("### Filters")
        confidence_threshold = st.slider(
            "Min Confidence",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            help="Only show bugs above this confidence score",
        )

        st.divider()
        st.markdown(
            """
            <div style='text-align:center; color:#484f58; font-size:12px'>
                <p>Agentic Bug Hunter v2.0</p>
                <p>Powered by Gemini + MCP</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Header ────────────────────────────────────────────────
    st.markdown('<p class="main-header">Agentic Bug Hunter</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Multi-agent system for detecting semantic bugs in C/C++ code</p>',
        unsafe_allow_html=True,
    )

    # ── Tabs ──────────────────────────────────────────────────
    tab_analyze, tab_results, tab_code, tab_benchmark, tab_pipeline, tab_about = st.tabs(
        ["Analyze", "Results", "Code View", "Benchmark", "Pipeline", "About"]
    )

    with tab_analyze:
        if analysis_mode == "Upload CSV":
            _render_csv_upload(use_mcp, use_severity, use_explanation, demo_mode)
        else:
            _render_code_paste(use_mcp, use_severity, use_explanation, demo_mode)

    with tab_results:
        _render_results(confidence_threshold)

    with tab_code:
        _render_code_annotation(confidence_threshold)

    with tab_benchmark:
        _render_benchmark()

    with tab_pipeline:
        _render_pipeline()

    with tab_about:
        _render_about()


# ──────────────────────────────────────────────────────────────
#  CSV Upload Mode
# ──────────────────────────────────────────────────────────────
def _render_csv_upload(use_mcp, use_severity, use_explanation, demo_mode):
    st.markdown("### Upload Code Samples")
    st.info("Upload a CSV file with columns: **ID**, **Code**")

    uploaded = st.file_uploader("Choose a samples CSV file", type=["csv"])

    if uploaded:
        content = uploaded.getvalue().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        samples = [{"ID": row["ID"], "Code": row["Code"]} for row in reader]

        st.success(f"Loaded **{len(samples)}** code samples")

        with st.expander("Preview Samples", expanded=False):
            for s in samples[:3]:
                st.markdown(f"**Sample {s['ID']}**")
                st.code(s["Code"][:500], language="cpp")

        if st.button("Run Analysis", type="primary", use_container_width=True):
            _run_analysis(samples, use_mcp, use_severity, use_explanation, demo_mode)


# ──────────────────────────────────────────────────────────────
#  Code Paste Mode
# ──────────────────────────────────────────────────────────────
def _render_code_paste(use_mcp, use_severity, use_explanation, demo_mode):
    st.markdown("### Paste Code for Analysis")
    sample_id = st.text_input("Sample ID", value="SAMPLE_001")
    code = st.text_area("C/C++ Code", height=400, placeholder="Paste your C/C++ source code here...")

    if code and st.button("Run Analysis", type="primary", use_container_width=True):
        samples = [{"ID": sample_id, "Code": code}]
        _run_analysis(samples, use_mcp, use_severity, use_explanation, demo_mode)


# ──────────────────────────────────────────────────────────────
#  Run Analysis
# ──────────────────────────────────────────────────────────────
def _run_analysis(samples, use_mcp, use_severity, use_explanation, demo_mode):
    orchestrator = Orchestrator()
    orchestrator.mcp_enabled = use_mcp
    orchestrator.severity_enabled = use_severity
    orchestrator.explanation_enabled = use_explanation
    orchestrator.demo_mode = demo_mode

    progress_bar = st.progress(0, text="Initializing pipeline...")
    status_text = st.empty()

    def update_progress(text, pct):
        progress_bar.progress(min(pct, 1.0), text=text)
        status_text.text(text)

    results, summary = orchestrator.analyze_batch(samples, progress_callback=update_progress)
    progress_bar.progress(1.0, text="Analysis complete.")

    st.session_state["results"] = results
    st.session_state["summary"] = summary

    generator = ReportGenerator()
    outputs = generator.generate_all(results, summary)
    st.session_state["report_files"] = outputs

    if demo_mode:
        st.info(f"**Demo mode** — loaded {summary.total_bugs} bugs from cache (zero API calls)")
    else:
        st.success(f"Found **{summary.total_bugs}** bugs across **{summary.total_samples}** samples.")

    _render_summary_metrics(summary)


# ──────────────────────────────────────────────────────────────
#  Summary Metrics
# ──────────────────────────────────────────────────────────────
def _render_summary_metrics(summary):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Samples", summary.total_samples)
    with col2:
        st.metric("Total Bugs", summary.total_bugs)
    with col3:
        st.metric("Avg / Sample", f"{summary.avg_bugs_per_sample:.1f}")
    with col4:
        st.metric("Critical", summary.bugs_by_severity.get("CRITICAL", 0))
    with col5:
        st.metric("High", summary.bugs_by_severity.get("HIGH", 0))
    with col6:
        st.metric("Time (s)", f"{summary.processing_time_ms / 1000:.1f}")


# ──────────────────────────────────────────────────────────────
#  Results Tab
# ──────────────────────────────────────────────────────────────
def _render_results(confidence_threshold):
    if "results" not in st.session_state:
        st.info("Run an analysis first to see results here.")
        return

    results = st.session_state["results"]
    summary = st.session_state["summary"]

    _render_summary_metrics(summary)
    st.divider()

    # Charts
    col_sev, col_cat = st.columns(2)
    with col_sev:
        st.markdown("#### Bugs by Severity")
        if summary.bugs_by_severity:
            import pandas as pd
            sev_df = pd.DataFrame(list(summary.bugs_by_severity.items()), columns=["Severity", "Count"])
            st.bar_chart(sev_df, x="Severity", y="Count", color="#58a6ff")
    with col_cat:
        st.markdown("#### Bugs by Category")
        if summary.bugs_by_category:
            import pandas as pd
            cat_df = pd.DataFrame(list(summary.bugs_by_category.items()), columns=["Category", "Count"])
            st.bar_chart(cat_df, x="Category", y="Count", color="#3fb950")

    st.divider()
    st.markdown("### Detailed Bug Reports")

    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        sev_filter = st.multiselect("Severity", [s.value for s in Severity], default=[s.value for s in Severity])
    with fcol2:
        cat_filter = st.multiselect("Category", [c.value for c in BugCategory], default=[c.value for c in BugCategory])
    with fcol3:
        sample_ids = list({r.sample_id for r in results})
        id_filter = st.multiselect("Sample ID", sample_ids, default=sample_ids)

    for result in results:
        if result.sample_id not in id_filter:
            continue
        for bug in result.bugs:
            if bug.severity.value not in sev_filter or bug.category.value not in cat_filter:
                continue
            if bug.confidence < confidence_threshold:
                continue

            sev_class = {"CRITICAL": "sev-critical", "HIGH": "sev-high", "MEDIUM": "sev-medium", "LOW": "sev-low"}
            cwe_html = f' <span class="cwe-badge">{bug.cwe_id}</span>' if bug.cwe_id else ""

            with st.expander(f"**{bug.id}** — Line {bug.bug_line} | {bug.severity.value} | {bug.category.value}"):
                st.markdown(
                    f'<span class="severity-badge {sev_class.get(bug.severity.value, "")}">{bug.severity.value}</span>{cwe_html}',
                    unsafe_allow_html=True,
                )
                if bug.cwe_id:
                    st.caption(f"{bug.cwe_id}: {bug.cwe_name}")
                st.markdown(f"**Explanation:** {bug.explanation}")
                st.code(bug.code_line, language="cpp")

                if bug.docs_context:
                    st.markdown("**Documentation Context:**")
                    st.caption(bug.docs_context[:300])

                mcol1, mcol2, mcol3 = st.columns(3)
                with mcol1:
                    st.metric("Confidence", f"{bug.confidence:.0%}")
                with mcol2:
                    st.metric("Line", bug.bug_line)
                with mcol3:
                    st.metric("Severity", bug.severity.value)

                if result.code:
                    st.markdown("**Code Context:**")
                    ctx = get_code_context(result.code, bug.bug_line, context_lines=5)
                    st.code(ctx, language="text")

    # Downloads
    st.divider()
    st.markdown("### Download Reports")
    report_files = st.session_state.get("report_files", {})
    dcol1, dcol2, dcol3 = st.columns(3)
    for col, (fmt, path) in zip([dcol1, dcol2, dcol3], report_files.items()):
        with col:
            if Path(path).exists():
                with open(path, "rb") as f:
                    st.download_button(
                        f"Download {fmt.upper()}", data=f.read(), file_name=Path(path).name,
                        mime="text/csv" if fmt == "csv" else "application/json" if fmt == "json" else "text/html",
                        use_container_width=True,
                    )


# ──────────────────────────────────────────────────────────────
#  Interactive Code Annotation View
# ──────────────────────────────────────────────────────────────
def _render_code_annotation(confidence_threshold):
    if "results" not in st.session_state:
        st.info("Run an analysis first to see annotated code here.")
        return

    results = st.session_state["results"]
    st.markdown("### Interactive Code Annotation")
    st.caption("Bug lines are highlighted inline. Hover for details.")

    for result in results:
        if not result.bugs:
            continue

        st.markdown(f"#### Sample: `{result.sample_id}`")

        # Build a map of line → bug info
        bug_map = {}
        for bug in result.bugs:
            if bug.confidence >= confidence_threshold:
                bug_map[bug.bug_line] = bug

        # Render annotated code
        lines = result.code.split("\n")
        html_lines = []
        for i, line in enumerate(lines, 1):
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if i in bug_map:
                b = bug_map[i]
                sev_colors = {"CRITICAL": "#da3633", "HIGH": "#d29922", "MEDIUM": "#58a6ff", "LOW": "#3fb950"}
                color = sev_colors.get(b.severity.value, "#58a6ff")
                bg = f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.12)"
                tooltip = f"{b.severity.value} | {b.category.value} | {b.cwe_id}&#10;{b.explanation[:120]}"
                html_lines.append(
                    f'<div class="code-line" style="background:{bg};border-left:3px solid {color}" title="{tooltip}">'
                    f'<span class="line-num">{i}</span>{escaped}'
                    f' <span style="color:{color};font-size:11px;margin-left:12px">◀ {b.severity.value}: {b.category.value}</span>'
                    f'</div>'
                )
            else:
                html_lines.append(
                    f'<div class="code-line"><span class="line-num">{i}</span>{escaped}</div>'
                )

        st.markdown(
            f'<div class="annotated-code">{"".join(html_lines)}</div>',
            unsafe_allow_html=True,
        )

        # Legend
        st.markdown(
            '<span style="color:#da3633">■</span> Critical &nbsp; '
            '<span style="color:#d29922">■</span> High &nbsp; '
            '<span style="color:#58a6ff">■</span> Medium &nbsp; '
            '<span style="color:#3fb950">■</span> Low',
            unsafe_allow_html=True,
        )
        st.divider()


# ──────────────────────────────────────────────────────────────
#  Benchmark Tab
# ──────────────────────────────────────────────────────────────
def _render_benchmark():
    if "results" not in st.session_state:
        st.info("Run an analysis first to see benchmark results.")
        return

    results = st.session_state["results"]
    evaluator = BenchmarkEvaluator()

    if not evaluator.has_ground_truth():
        st.warning("No ground truth data found. Create `data/ground_truth.json`.")
        return

    st.markdown("### Benchmark Evaluation")
    st.caption("Comparing detected bugs against ground truth annotations")

    metrics = evaluator.evaluate_batch(results)

    # Aggregate metrics cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        color = "#3fb950" if metrics.precision >= 0.8 else "#d29922" if metrics.precision >= 0.5 else "#da3633"
        st.markdown(f'<div class="benchmark-card"><div class="benchmark-value" style="color:{color}">{metrics.precision:.0%}</div><div class="benchmark-label">Precision</div></div>', unsafe_allow_html=True)
    with col2:
        color = "#3fb950" if metrics.recall >= 0.8 else "#d29922" if metrics.recall >= 0.5 else "#da3633"
        st.markdown(f'<div class="benchmark-card"><div class="benchmark-value" style="color:{color}">{metrics.recall:.0%}</div><div class="benchmark-label">Recall</div></div>', unsafe_allow_html=True)
    with col3:
        color = "#3fb950" if metrics.f1_score >= 0.8 else "#d29922" if metrics.f1_score >= 0.5 else "#da3633"
        st.markdown(f'<div class="benchmark-card"><div class="benchmark-value" style="color:{color}">{metrics.f1_score:.2f}</div><div class="benchmark-label">F1-Score</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="benchmark-card"><div class="benchmark-value" style="color:#3fb950">{metrics.total_true_positives}</div><div class="benchmark-label">True Positives</div></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="benchmark-card"><div class="benchmark-value" style="color:#da3633">{metrics.total_false_positives}</div><div class="benchmark-label">False Positives</div></div>', unsafe_allow_html=True)
    with col6:
        st.markdown(f'<div class="benchmark-card"><div class="benchmark-value" style="color:#d29922">{metrics.total_false_negatives}</div><div class="benchmark-label">False Negatives</div></div>', unsafe_allow_html=True)

    st.divider()

    # Per-sample breakdown
    st.markdown("### Per-Sample Results")
    for sr in metrics.per_sample:
        with st.expander(f"**{sr.sample_id}** — P={sr.precision:.0%}  R={sr.recall:.0%}  F1={sr.f1_score:.2f}"):
            pcol1, pcol2, pcol3 = st.columns(3)
            with pcol1:
                st.metric("Precision", f"{sr.precision:.0%}")
            with pcol2:
                st.metric("Recall", f"{sr.recall:.0%}")
            with pcol3:
                st.metric("F1-Score", f"{sr.f1_score:.2f}")

            if sr.matched_lines:
                st.success(f"✅ **Matched lines:** {sr.matched_lines}")
            if sr.missed_lines:
                st.error(f"❌ **Missed lines:** {sr.missed_lines}")
            if sr.extra_lines:
                st.warning(f"⚠️ **Extra detections:** {sr.extra_lines}")


# ──────────────────────────────────────────────────────────────
#  Pipeline View (DAG Visualization)
# ──────────────────────────────────────────────────────────────
def _render_pipeline():
    st.markdown("### Pipeline Architecture")

    has_results = "results" in st.session_state

    # Build dynamic DAG based on execution state
    agents = [
        {"name": "Input", "icon": "📄", "desc": "CSV / Paste Code", "agent_name": None},
        {"name": "Reasoning Agent", "icon": "🧠", "desc": "Bug Discovery (Gemini)", "agent_name": "ReasoningAgent"},
        {"name": "MCP Knowledge Agent", "icon": "📚", "desc": "Documentation Grounding", "agent_name": "MCPKnowledgeAgent"},
        {"name": "Severity Agent", "icon": "⚠️", "desc": "Risk Classification", "agent_name": "SeverityAgent"},
        {"name": "Explanation Agent", "icon": "✏️", "desc": "Report Refinement", "agent_name": "ExplanationAgent"},
        {"name": "Output", "icon": "📊", "desc": "CSV + HTML + JSON", "agent_name": None},
    ]

    # Get timing data from traces if available
    timing = {}
    if has_results:
        for result in st.session_state["results"]:
            for event in result.agent_trace:
                timing[event.agent_name] = {
                    "ms": event.duration_ms,
                    "status": event.status,
                }

    cols = st.columns(len(agents))
    for i, (col, agent) in enumerate(zip(cols, agents)):
        with col:
            status_icon = ""
            timing_text = ""
            border_color = "#30363d"

            if agent["agent_name"] and has_results:
                t = timing.get(agent["agent_name"])
                if t:
                    status_icon = "✅" if t["status"] == "success" else "❌"
                    timing_text = f"<br><span style='color:#8b949e;font-size:11px'>{t['ms']:.0f}ms</span>"
                    border_color = "#3fb950" if t["status"] == "success" else "#da3633"
            elif not agent["agent_name"] and has_results:
                status_icon = "✅"
                border_color = "#3fb950"

            st.markdown(
                f'<div style="background:#161b22;border:2px solid {border_color};border-radius:10px;padding:16px;text-align:center;min-height:120px">'
                f'<div style="font-size:28px">{agent["icon"]}</div>'
                f'<div style="font-weight:600;font-size:13px;margin-top:6px">{agent["name"]} {status_icon}</div>'
                f'<div style="color:#8b949e;font-size:11px">{agent["desc"]}</div>'
                f'{timing_text}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Agent trace details
    if has_results:
        st.divider()
        st.markdown("### Agent Execution Trace")
        for result in st.session_state["results"]:
            with st.expander(f"Sample {result.sample_id} — {len(result.agent_trace)} events"):
                for i, event in enumerate(result.agent_trace):
                    status = "✅" if event.status == "success" else "❌"
                    st.markdown(
                        f"**{i + 1}.** {status} `{event.agent_name}` — "
                        f"{event.duration_ms:.0f}ms — {event.output_summary[:100]}"
                    )


# ──────────────────────────────────────────────────────────────
#  About Tab
# ──────────────────────────────────────────────────────────────
def _render_about():
    st.markdown("""
    ### About Agentic Bug Hunter

    **Agentic Bug Hunter** is a multi-agent system designed to automatically detect
    semantic bugs in C/C++ programs.

    #### Agent Architecture

    | Agent | Role | Technology |
    |-------|------|------------|
    | **Reasoning Agent** | Bug discovery via LLM analysis | Google Gemini 2.5 Flash |
    | **MCP Knowledge Agent** | Documentation grounding | MCP Server (FastMCP) |
    | **Severity Agent** | Risk classification | Gemini-based classification |
    | **Explanation Agent** | Report refinement | Gemini with dataset-style formatting |

    #### Key Features
    - Multi-agent pipeline with clear separation of concerns
    - **Demo/Cache mode** — zero API calls for reliable presentations
    - **CWE taxonomy mapping** — industry-standard vulnerability classification
    - **Ground truth benchmarking** — Precision, Recall, F1-Score evaluation
    - **Interactive code annotation** — bugs highlighted inline with severity colors
    - **Confidence threshold filtering** — adjustable bug sensitivity
    - Real-time progress tracking with agent execution traces
    - Severity classification (Critical / High / Medium / Low)
    - Bug categorization (API Misuse, Logic Error, Resource Management, etc.)
    - Multi-format report generation (CSV, HTML, JSON)
    - MCP-based documentation grounding for verified explanations

    #### CWE Mapping Reference

    | Category | CWE ID | CWE Name |
    |----------|--------|----------|""")

    for cat, cwe in CWE_MAPPING.items():
        st.markdown(f"    | {cat} | {cwe['id']} | {cwe['name']} |")


if __name__ == "__main__":
    main()
