"""Agentic Bug Hunter - CLI Entry Point.

Usage:
    python -m src.main --input data/samples.csv
    python -m src.main --input data/samples.csv --formats csv html json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.orchestrator import Orchestrator
from src.reports.generator import ReportGenerator
from src.utils.helpers import read_samples_csv
from src.utils.logger import logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agentic Bug Hunter — Multi-Agent Semantic Bug Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="data/samples.csv",
        help="Path to input CSV file with 'ID' and 'Code' columns",
    )
    parser.add_argument(
        "--formats", "-f",
        nargs="+",
        choices=["csv", "html", "json"],
        default=["csv", "html", "json"],
        help="Report output formats (default: csv html json)",
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Disable MCP documentation grounding",
    )
    parser.add_argument(
        "--no-severity",
        action="store_true",
        help="Disable severity classification",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("  AGENTIC BUG HUNTER — Multi-Agent Pipeline")
    logger.info("=" * 60)

    # Read input
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    samples = read_samples_csv(input_path)
    logger.info(f"Loaded {len(samples)} code samples from {input_path}")

    # Initialize pipeline
    orchestrator = Orchestrator()
    orchestrator.mcp_enabled = not args.no_mcp
    orchestrator.severity_enabled = not args.no_severity

    # Run analysis
    logger.info("Starting analysis pipeline...")

    def cli_progress(text: str, pct: float):
        bar_len = 30
        filled = int(bar_len * pct)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  [{bar}] {pct:.0%} — {text}", end="", flush=True)

    results, summary = orchestrator.analyze_batch(samples, progress_callback=cli_progress)
    print()  # newline after progress bar

    # Print summary
    logger.info("-" * 60)
    logger.info(f"  Samples Analyzed : {summary.total_samples}")
    logger.info(f"  Total Bugs Found : {summary.total_bugs}")
    logger.info(f"  Avg Bugs/Sample  : {summary.avg_bugs_per_sample:.1f}")
    logger.info(f"  Processing Time  : {summary.processing_time_ms / 1000:.1f}s")
    logger.info(f"  By Severity      : {dict(summary.bugs_by_severity)}")
    logger.info(f"  By Category      : {dict(summary.bugs_by_category)}")
    logger.info("-" * 60)

    # Generate reports
    generator = ReportGenerator()
    outputs = generator.generate_all(results, summary, formats=args.formats)

    logger.info("Reports generated:")
    for fmt, path in outputs.items():
        logger.info(f"  {fmt.upper()}: {path}")

    logger.info("=" * 60)
    logger.info("  DONE.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
