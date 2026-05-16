"""CLI entry point for Agentic Bug Hunter.

Usage:
    python -m src.main --input data/samples.csv
    python -m src.main --input data/samples.csv --demo    # Cache-only mode (no API calls)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.orchestrator import Orchestrator
from src.reports.generator import ReportGenerator
from src.evaluation.benchmark import BenchmarkEvaluator
from src.utils.helpers import read_samples_csv
from src.utils.logger import logger


def main():
    parser = argparse.ArgumentParser(
        description="Agentic Bug Hunter — Multi-agent C/C++ bug detection system"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input CSV file with columns: ID, Code",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo mode: use cached results only (zero API calls)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run benchmark evaluation against ground truth",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (always call API, don't read/write cache)",
    )

    args = parser.parse_args()

    # Load samples
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    samples = read_samples_csv(input_path)
    logger.info(f"Loaded {len(samples)} code samples from {input_path}")

    # Initialize orchestrator
    orchestrator = Orchestrator()

    if args.demo:
        orchestrator.demo_mode = True
        logger.info("Running in DEMO mode (cached results only, zero API calls)")

    if args.no_cache:
        orchestrator.cache_enabled = False
        orchestrator.cache = None
        logger.info("Caching disabled")

    # Run analysis
    def progress(text, pct):
        logger.info(f"[{pct:.0%}] {text}")

    results, summary = orchestrator.analyze_batch(samples, progress_callback=progress)

    # Print summary
    print("\n" + "=" * 60)
    print("  ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"  Samples analyzed: {summary.total_samples}")
    print(f"  Total bugs found: {summary.total_bugs}")
    print(f"  Avg bugs/sample:  {summary.avg_bugs_per_sample:.1f}")
    print(f"  Processing time:  {summary.processing_time_ms / 1000:.1f}s")
    print()

    if summary.bugs_by_severity:
        print("  Severity Breakdown:")
        for sev, count in sorted(summary.bugs_by_severity.items()):
            print(f"    {sev:10s}: {count}")
    print()

    if summary.bugs_by_category:
        print("  Category Breakdown:")
        for cat, count in sorted(summary.bugs_by_category.items()):
            print(f"    {cat:15s}: {count}")
    print("=" * 60)

    # Generate reports
    generator = ReportGenerator()
    outputs = generator.generate_all(results, summary)
    for fmt, path in outputs.items():
        print(f"  {fmt.upper()} report: {path}")

    # Run benchmark if requested
    if args.benchmark:
        print("\n" + "=" * 60)
        print("  BENCHMARK EVALUATION")
        print("=" * 60)
        evaluator = BenchmarkEvaluator()
        if evaluator.has_ground_truth():
            metrics = evaluator.evaluate_batch(results)
            print(f"  Samples evaluated: {metrics.total_samples}")
            print(f"  True Positives:    {metrics.total_true_positives}")
            print(f"  False Positives:   {metrics.total_false_positives}")
            print(f"  False Negatives:   {metrics.total_false_negatives}")
            print(f"  Precision:         {metrics.precision:.1%}")
            print(f"  Recall:            {metrics.recall:.1%}")
            print(f"  F1-Score:          {metrics.f1_score:.3f}")
            print()
            for sr in metrics.per_sample:
                print(f"  [{sr.sample_id}] P={sr.precision:.0%} R={sr.recall:.0%} F1={sr.f1_score:.2f}"
                      f"  TP={sr.true_positives} FP={sr.false_positives} FN={sr.false_negatives}")
                if sr.matched_lines:
                    print(f"    ✅ Matched lines: {sr.matched_lines}")
                if sr.missed_lines:
                    print(f"    ❌ Missed lines:  {sr.missed_lines}")
                if sr.extra_lines:
                    print(f"    ⚠️  Extra lines:   {sr.extra_lines}")
        else:
            print("  No ground truth data found. Create data/ground_truth.json")
        print("=" * 60)


if __name__ == "__main__":
    main()
