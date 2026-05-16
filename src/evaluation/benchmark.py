"""Benchmark Evaluator - Compares detected bugs against ground truth.

Computes Precision, Recall, F1-Score, and line-level accuracy
to quantify the system's bug detection performance.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field

from src.models.schemas import AnalysisResult
from src.utils.logger import logger

GROUND_TRUTH_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ground_truth.json"


@dataclass
class BenchmarkResult:
    """Results from evaluating against ground truth."""
    sample_id: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    matched_lines: list = field(default_factory=list)
    missed_lines: list = field(default_factory=list)
    extra_lines: list = field(default_factory=list)


@dataclass
class AggregateMetrics:
    """Aggregate benchmark metrics across all samples."""
    total_samples: int = 0
    total_true_positives: int = 0
    total_false_positives: int = 0
    total_false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    per_sample: list = field(default_factory=list)


class BenchmarkEvaluator:
    """Evaluates detected bugs against a ground truth dataset.

    Ground truth format (data/ground_truth.json):
    {
        "S001": {
            "bugs": [
                {"line": 9, "category": "RESOURCE_MGMT", "description": "..."},
                ...
            ]
        }
    }
    """

    def __init__(self, ground_truth_path: Path | None = None):
        self.gt_path = ground_truth_path or GROUND_TRUTH_PATH
        self.ground_truth = self._load_ground_truth()

    def _load_ground_truth(self) -> dict:
        """Load ground truth data from JSON file."""
        if not self.gt_path.exists():
            logger.warning(f"[Benchmark] Ground truth file not found: {self.gt_path}")
            return {}
        try:
            with open(self.gt_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter out metadata keys (e.g., _meta)
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"[Benchmark] Failed to load ground truth: {e}")
            return {}

    def evaluate_sample(
        self, result: AnalysisResult, line_tolerance: int = 1
    ) -> BenchmarkResult | None:
        """Evaluate a single sample's results against ground truth.

        Args:
            result: The analysis result to evaluate.
            line_tolerance: Allow ±N lines when matching bug locations.
                            Default is 1 (exact or off-by-one match).

        Returns:
            BenchmarkResult or None if no ground truth exists for this sample.
        """
        gt_entry = self.ground_truth.get(result.sample_id)
        if gt_entry is None:
            return None

        gt_bugs = gt_entry.get("bugs", [])
        gt_lines = [b["line"] for b in gt_bugs]
        detected_lines = [b.bug_line for b in result.bugs]

        # Match detected bugs to ground truth with tolerance
        matched_gt = set()
        matched_det = set()

        for i, det_line in enumerate(detected_lines):
            for j, gt_line in enumerate(gt_lines):
                if j not in matched_gt and abs(det_line - gt_line) <= line_tolerance:
                    matched_gt.add(j)
                    matched_det.add(i)
                    break

        tp = len(matched_gt)
        fp = len(detected_lines) - len(matched_det)
        fn = len(gt_lines) - len(matched_gt)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        matched = [gt_lines[j] for j in matched_gt]
        missed = [gt_lines[j] for j in range(len(gt_lines)) if j not in matched_gt]
        extra = [detected_lines[i] for i in range(len(detected_lines)) if i not in matched_det]

        return BenchmarkResult(
            sample_id=result.sample_id,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            matched_lines=matched,
            missed_lines=missed,
            extra_lines=extra,
        )

    def evaluate_batch(
        self, results: list[AnalysisResult], line_tolerance: int = 1
    ) -> AggregateMetrics:
        """Evaluate all results against ground truth and compute aggregate metrics.

        Args:
            results: List of analysis results to evaluate.
            line_tolerance: Allow ±N lines when matching.

        Returns:
            AggregateMetrics with per-sample and aggregate scores.
        """
        per_sample = []
        total_tp = total_fp = total_fn = 0

        for result in results:
            br = self.evaluate_sample(result, line_tolerance)
            if br is not None:
                per_sample.append(br)
                total_tp += br.true_positives
                total_fp += br.false_positives
                total_fn += br.false_negatives

        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return AggregateMetrics(
            total_samples=len(per_sample),
            total_true_positives=total_tp,
            total_false_positives=total_fp,
            total_false_negatives=total_fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            per_sample=per_sample,
        )

    def has_ground_truth(self) -> bool:
        """Check if ground truth data is available."""
        return bool(self.ground_truth)

    def get_sample_ids(self) -> list[str]:
        """Get list of sample IDs that have ground truth."""
        return list(self.ground_truth.keys())
