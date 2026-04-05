from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.error_analysis import run_benchmark_error_analysis


class ErrorAnalysisTest(unittest.TestCase):
    def test_run_benchmark_error_analysis_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            predictions_path = root / "predictions.csv"
            output_prefix = root / "error_analysis"

            fieldnames = [
                "timestamp",
                "own_mmsi",
                "target_mmsi",
                "label_future_conflict",
                "rule_score_score",
                "rule_score_pred",
                "logreg_score",
                "logreg_pred",
            ]
            rows = [
                {
                    "timestamp": "2026-03-09T09:00:00Z",
                    "own_mmsi": "440000001",
                    "target_mmsi": "440000101",
                    "label_future_conflict": "1",
                    "rule_score_score": "0.90",
                    "rule_score_pred": "1",
                    "logreg_score": "0.95",
                    "logreg_pred": "1",
                },
                {
                    "timestamp": "2026-03-09T09:01:00Z",
                    "own_mmsi": "440000001",
                    "target_mmsi": "440000102",
                    "label_future_conflict": "0",
                    "rule_score_score": "0.88",
                    "rule_score_pred": "1",
                    "logreg_score": "0.80",
                    "logreg_pred": "1",
                },
                {
                    "timestamp": "2026-03-09T09:02:00Z",
                    "own_mmsi": "440000001",
                    "target_mmsi": "440000103",
                    "label_future_conflict": "1",
                    "rule_score_score": "0.10",
                    "rule_score_pred": "0",
                    "logreg_score": "0.20",
                    "logreg_pred": "0",
                },
                {
                    "timestamp": "2026-03-09T09:03:00Z",
                    "own_mmsi": "440000001",
                    "target_mmsi": "440000104",
                    "label_future_conflict": "0",
                    "rule_score_score": "0.05",
                    "rule_score_pred": "0",
                    "logreg_score": "0.10",
                    "logreg_pred": "0",
                },
            ]
            with predictions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            summary = run_benchmark_error_analysis(
                predictions_csv_path=predictions_path,
                output_prefix=output_prefix,
                model_names=["rule_score", "logreg"],
                top_k_each=2,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(4, summary["selected_error_row_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["error_cases_csv_path"]).exists())


if __name__ == "__main__":
    unittest.main()
