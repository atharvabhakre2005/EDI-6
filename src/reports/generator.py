"""Multi-format report generator for bug analysis results."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from src.models.schemas import AnalysisResult, AnalysisSummary, BugReport
from src.utils.config import get_output_dir
from src.utils.logger import logger


class ReportGenerator:
    """Generates analysis reports in multiple formats (CSV, HTML, JSON)."""

    def __init__(self):
        self.output_dir = get_output_dir()

    def generate_all(
        self,
        results: list[AnalysisResult],
        summary: AnalysisSummary,
        formats: list[str] | None = None,
    ) -> dict[str, Path]:
        """Generate reports in all configured formats.

        Returns:
            dict mapping format name to output file path.
        """
        if formats is None:
            formats = ["csv", "html", "json"]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outputs: dict[str, Path] = {}

        all_bugs = []
        for r in results:
            all_bugs.extend(r.bugs)

        if "csv" in formats:
            outputs["csv"] = self._generate_csv(all_bugs, timestamp)
        if "json" in formats:
            outputs["json"] = self._generate_json(results, summary, timestamp)
        if "html" in formats:
            outputs["html"] = self._generate_html(results, summary, timestamp)

        return outputs

    def _generate_csv(self, bugs: list[BugReport], timestamp: str) -> Path:
        """Generate CSV report matching the hackathon output format."""
        path = self.output_dir / f"final_report_{timestamp}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["ID", "bug_line", "Explanation"]
            )
            writer.writeheader()
            for bug in bugs:
                writer.writerow({
                    "ID": bug.id,
                    "bug_line": bug.bug_line,
                    "Explanation": bug.explanation,
                })
        logger.info(f"CSV report saved: {path}")
        return path

    def _generate_json(
        self,
        results: list[AnalysisResult],
        summary: AnalysisSummary,
        timestamp: str,
    ) -> Path:
        """Generate detailed JSON report with full analysis data."""
        path = self.output_dir / f"analysis_report_{timestamp}.json"
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary.model_dump(mode="json"),
            "results": [r.model_dump(mode="json") for r in results],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"JSON report saved: {path}")
        return path

    def _generate_html(
        self,
        results: list[AnalysisResult],
        summary: AnalysisSummary,
        timestamp: str,
    ) -> Path:
        """Generate a professional HTML report with dashboard-style layout."""
        path = self.output_dir / f"bug_report_{timestamp}.html"

        severity_colors = {
            "CRITICAL": "#dc3545",
            "HIGH": "#fd7e14",
            "MEDIUM": "#ffc107",
            "LOW": "#28a745",
        }

        # Build bugs HTML
        bugs_html = ""
        for result in results:
            for bug in result.bugs:
                sev_color = severity_colors.get(bug.severity.value, "#6c757d")
                bugs_html += f"""
                <tr>
                    <td><code>{bug.id}</code></td>
                    <td class="text-center">{bug.bug_line}</td>
                    <td><span class="badge" style="background-color:{sev_color}">{bug.severity.value}</span></td>
                    <td><span class="badge badge-category">{bug.category.value}</span></td>
                    <td>{bug.explanation}</td>
                    <td><code>{_escape_html(bug.code_line)}</code></td>
                    <td>{bug.confidence:.0%}</td>
                </tr>"""

        # Build severity chart data
        sev_data = summary.bugs_by_severity
        cat_data = summary.bugs_by_category

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic Bug Hunter Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0d1117; color: #c9d1d9; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #161b22, #1f2937); padding: 30px; border-radius: 12px; margin-bottom: 24px; border: 1px solid #30363d; }}
        .header h1 {{ font-size: 28px; color: #58a6ff; margin-bottom: 8px; }}
        .header p {{ color: #8b949e; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .stat-card {{ background: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d; text-align: center; }}
        .stat-card .value {{ font-size: 36px; font-weight: bold; color: #58a6ff; }}
        .stat-card .label {{ font-size: 14px; color: #8b949e; margin-top: 4px; }}
        .section {{ background: #161b22; border-radius: 10px; padding: 24px; margin-bottom: 24px; border: 1px solid #30363d; }}
        .section h2 {{ color: #58a6ff; margin-bottom: 16px; font-size: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #1f2937; color: #58a6ff; padding: 12px 16px; text-align: left; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
        td {{ padding: 12px 16px; border-bottom: 1px solid #21262d; font-size: 14px; }}
        tr:hover {{ background: #1f2937; }}
        code {{ background: #1f2937; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #f0883e; }}
        .badge {{ color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; display: inline-block; }}
        .badge-category {{ background: #1f6feb; }}
        .text-center {{ text-align: center; }}
        .charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
        .chart-container {{ background: #161b22; border-radius: 10px; padding: 24px; border: 1px solid #30363d; }}
        .chart-container h3 {{ color: #58a6ff; margin-bottom: 16px; }}
        .bar {{ height: 32px; border-radius: 6px; margin-bottom: 8px; display: flex; align-items: center; padding: 0 12px; font-size: 13px; font-weight: 600; color: white; min-width: 40px; }}
        .bar-label {{ display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px; }}
        .footer {{ text-align: center; padding: 20px; color: #484f58; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>&#128027; Agentic Bug Hunter Report</h1>
            <p>Multi-Agent AI Analysis | Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')} | Infineon RDI Code Analysis</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="value">{summary.total_samples}</div>
                <div class="label">Samples Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="value">{summary.total_bugs}</div>
                <div class="label">Bugs Detected</div>
            </div>
            <div class="stat-card">
                <div class="value">{summary.avg_bugs_per_sample:.1f}</div>
                <div class="label">Avg Bugs / Sample</div>
            </div>
            <div class="stat-card">
                <div class="value">{summary.processing_time_ms / 1000:.1f}s</div>
                <div class="label">Processing Time</div>
            </div>
            <div class="stat-card">
                <div class="value" style="color: #dc3545">{sev_data.get('CRITICAL', 0)}</div>
                <div class="label">Critical Bugs</div>
            </div>
            <div class="stat-card">
                <div class="value" style="color: #fd7e14">{sev_data.get('HIGH', 0)}</div>
                <div class="label">High Severity</div>
            </div>
        </div>

        <div class="charts">
            <div class="chart-container">
                <h3>Bugs by Severity</h3>
                {self._build_bar_chart(sev_data, severity_colors)}
            </div>
            <div class="chart-container">
                <h3>Bugs by Category</h3>
                {self._build_bar_chart(cat_data, None)}
            </div>
        </div>

        <div class="section">
            <h2>Detailed Bug Report</h2>
            <table>
                <thead>
                    <tr>
                        <th>Sample ID</th>
                        <th>Line</th>
                        <th>Severity</th>
                        <th>Category</th>
                        <th>Explanation</th>
                        <th>Code</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    {bugs_html}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Agentic Bug Hunter v1.0 | Powered by Gemini + MCP | Infineon RDI Analysis Platform</p>
        </div>
    </div>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML report saved: {path}")
        return path

    def _build_bar_chart(
        self, data: dict[str, int], colors: dict[str, str] | None
    ) -> str:
        """Build a simple CSS bar chart."""
        if not data:
            return "<p style='color:#8b949e'>No data available</p>"

        max_val = max(data.values()) if data else 1
        default_colors = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff", "#79c0ff", "#56d364"]
        bars = ""
        for i, (label, count) in enumerate(sorted(data.items(), key=lambda x: -x[1])):
            if colors and label in colors:
                color = colors[label]
            else:
                color = default_colors[i % len(default_colors)]
            width = max(count / max_val * 100, 8)
            bars += f"""
                <div class="bar-label"><span>{label}</span><span>{count}</span></div>
                <div class="bar" style="width:{width}%;background:{color}">{count}</div>"""
        return bars


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
