"""Orchestrator - Coordinates the multi-agent pipeline for bug analysis."""

from __future__ import annotations

from datetime import datetime

from src.agents.base_agent import BaseAgent
from src.agents.reasoning_agent import ReasoningAgent
from src.agents.mcp_agent import MCPKnowledgeAgent
from src.agents.severity_agent import SeverityAgent
from src.agents.explanation_agent import ExplanationAgent
from src.models.schemas import (
    BugReport,
    AnalysisResult,
    AgentEvent,
    AnalysisSummary,
    Severity,
)
from src.utils.config import load_settings
from src.utils.helpers import get_code_line, Timer
from src.utils.logger import logger


class Orchestrator:
    """Coordinates the multi-agent bug hunting pipeline.

    Pipeline flow:
    1. ReasoningAgent discovers bug hypotheses via Gemini
    2. MCPKnowledgeAgent grounds each bug against documentation
    3. SeverityAgent classifies bug severity
    4. ExplanationAgent refines the final explanation

    All agent events are traced for observability.
    """

    def __init__(self):
        settings = load_settings()
        agent_cfg = settings.get("agents", {})

        self.reasoner = ReasoningAgent()
        self.mcp = MCPKnowledgeAgent()
        self.severity_clf = SeverityAgent()
        self.explainer = ExplanationAgent()

        self.mcp_enabled = agent_cfg.get("mcp_knowledge", {}).get("enabled", True)
        self.severity_enabled = agent_cfg.get("severity", {}).get("enabled", True)
        self.explanation_enabled = agent_cfg.get("explanation", {}).get("enabled", True)

    def analyze_sample(
        self, sample_id: str, code: str, progress_callback=None
    ) -> AnalysisResult:
        """Run the full multi-agent pipeline on a single code sample.

        Args:
            sample_id: Unique identifier for the code sample.
            code: The C++ source code to analyze.
            progress_callback: Optional callable(status_text, progress_pct) for UI.

        Returns:
            AnalysisResult with all detected bugs and agent trace.
        """
        timer = Timer()
        trace: list[AgentEvent] = []
        reports: list[BugReport] = []

        with timer:
            # --- Step 1: Reasoning Agent — discover bugs ---
            if progress_callback:
                progress_callback("Analyzing code with Gemini...", 0.1)

            raw_bugs, event = self.reasoner.run(code)
            trace.append(event)

            if not raw_bugs:
                logger.info(f"[Orchestrator] No bugs found in sample {sample_id}")
                return AnalysisResult(
                    sample_id=sample_id,
                    code=code,
                    bugs=[],
                    agent_trace=trace,
                    processing_time_ms=timer.elapsed_ms,
                )

            total_bugs = len(raw_bugs)
            logger.info(
                f"[Orchestrator] Found {total_bugs} bug hypotheses in {sample_id}"
            )

            # --- Step 2: MCP grounding for each bug (no LLM calls) ---
            docs_list = []
            for i, bug in enumerate(raw_bugs):
                code_line_text = get_code_line(code, bug.line)
                docs_text = ""
                if self.mcp_enabled:
                    if progress_callback:
                        progress_callback(
                            f"Grounding bug {i + 1}/{total_bugs} with MCP...", 0.2 + (0.2 * i / total_bugs)
                        )
                    docs, event = self.mcp.run(code_line_text)
                    trace.append(event)
                    if docs:
                        docs_text = self.mcp.get_docs_text(docs)
                docs_list.append(docs_text)

            # --- Step 3: Batch severity classification (1 API call) ---
            severity_results = [(Severity.MEDIUM, "")] * total_bugs
            if self.severity_enabled:
                if progress_callback:
                    progress_callback(
                        f"Classifying severity for {total_bugs} bugs (batch)...", 0.5
                    )
                sev_input = [
                    {
                        "index": i,
                        "summary": bug.summary,
                        "code_line": get_code_line(code, bug.line),
                        "category": bug.category.value,
                        "docs": docs_list[i][:300],
                    }
                    for i, bug in enumerate(raw_bugs)
                ]
                sev_results_raw, event = self.severity_clf.run(sev_input)
                trace.append(event)
                if sev_results_raw:
                    severity_results = sev_results_raw

            # --- Step 4: Batch explanation refinement (1 API call) ---
            explanations = [bug.summary for bug in raw_bugs]
            if self.explanation_enabled:
                if progress_callback:
                    progress_callback(
                        f"Refining explanations for {total_bugs} bugs (batch)...", 0.7
                    )
                exp_input = [
                    {
                        "index": i,
                        "summary": bug.summary,
                        "code_line": get_code_line(code, bug.line),
                        "docs": docs_list[i][:300],
                        "severity": severity_results[i][0].value if i < len(severity_results) else "MEDIUM",
                        "category": bug.category.value,
                    }
                    for i, bug in enumerate(raw_bugs)
                ]
                exp_results, event = self.explainer.run(exp_input)
                trace.append(event)
                if exp_results:
                    explanations = exp_results

            # --- Build final reports ---
            for i, bug in enumerate(raw_bugs):
                severity = severity_results[i][0] if i < len(severity_results) else Severity.MEDIUM
                explanation = explanations[i] if i < len(explanations) else bug.summary

                reports.append(
                    BugReport(
                        id=sample_id,
                        bug_line=bug.line,
                        category=bug.category,
                        severity=severity,
                        confidence=bug.confidence,
                        explanation=explanation,
                        raw_summary=bug.summary,
                        docs_context=docs_list[i][:500] if i < len(docs_list) else "",
                        code_line=get_code_line(code, bug.line),
                    )
                )

        if progress_callback:
            progress_callback("Analysis complete!", 1.0)

        return AnalysisResult(
            sample_id=sample_id,
            code=code,
            bugs=reports,
            timestamp=datetime.now(),
            agent_trace=trace,
            processing_time_ms=timer.elapsed_ms,
        )

    def analyze_batch(
        self,
        samples: list[dict[str, str]],
        progress_callback=None,
    ) -> tuple[list[AnalysisResult], AnalysisSummary]:
        """Analyze a batch of code samples.

        Args:
            samples: List of dicts with 'ID' and 'Code' keys.
            progress_callback: Optional callable(status, pct) for UI.

        Returns:
            tuple: (list of AnalysisResult, AnalysisSummary)
        """
        batch_timer = Timer()
        results: list[AnalysisResult] = []

        with batch_timer:
            total = len(samples)
            for idx, sample in enumerate(samples):
                if progress_callback:
                    progress_callback(
                        f"Processing sample {idx + 1}/{total}: {sample['ID']}",
                        idx / total,
                    )

                result = self.analyze_sample(sample["ID"], sample["Code"])
                results.append(result)

        # Compute summary statistics
        summary = self._compute_summary(results, batch_timer.elapsed_ms)

        if progress_callback:
            progress_callback("Batch analysis complete!", 1.0)

        return results, summary

    def _compute_summary(
        self, results: list[AnalysisResult], total_ms: float
    ) -> AnalysisSummary:
        """Compute aggregate statistics from analysis results."""
        total_bugs = sum(len(r.bugs) for r in results)
        bugs_by_severity: dict[str, int] = {}
        bugs_by_category: dict[str, int] = {}

        for r in results:
            for bug in r.bugs:
                sev = bug.severity.value
                bugs_by_severity[sev] = bugs_by_severity.get(sev, 0) + 1
                cat = bug.category.value
                bugs_by_category[cat] = bugs_by_category.get(cat, 0) + 1

        return AnalysisSummary(
            total_samples=len(results),
            total_bugs=total_bugs,
            bugs_by_severity=bugs_by_severity,
            bugs_by_category=bugs_by_category,
            avg_bugs_per_sample=total_bugs / max(len(results), 1),
            processing_time_ms=total_ms,
        )
