from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.calibration_eval import run_calibration_evaluation


class CalibrationEvalTest(unittest.TestCase):
    def test_run_calibration_evaluation_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            predictions_path = root / "predictions.csv"
            output_prefix = root / "calibration_eval"

            fieldnames = [
                "timestamp",
                "own_mmsi",
                "target_mmsi",
                "label_future_conflict",
                "logreg_score",
                "logreg_pred",
                "rule_score_score",
                "rule_score_pred",
            ]
            with predictions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "timestamp": "2026-03-09T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000101",
                            "label_future_conflict": "1",
                            "logreg_score": "0.90",
                            "logreg_pred": "1",
                            "rule_score_score": "0.85",
                            "rule_score_pred": "1",
                        },
                        {
                            "timestamp": "2026-03-09T09:01:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000102",
                            "label_future_conflict": "0",
                            "logreg_score": "0.80",
                            "logreg_pred": "1",
                            "rule_score_score": "0.25",
                            "rule_score_pred": "0",
                        },
                        {
                            "timestamp": "2026-03-09T09:02:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000103",
                            "label_future_conflict": "1",
                            "logreg_score": "0.40",
                            "logreg_pred": "0",
                            "rule_score_score": "0.70",
                            "rule_score_pred": "1",
                        },
                        {
                            "timestamp": "2026-03-09T09:03:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000104",
                            "label_future_conflict": "0",
                            "logreg_score": "0.10",
                            "logreg_pred": "0",
                            "rule_score_score": "0.15",
                            "rule_score_pred": "0",
                        },
                    ]
                )

            summary = run_calibration_evaluation(
                predictions_csv_path=predictions_path,
                output_prefix=output_prefix,
                num_bins=5,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(5, summary["bin_count"])
            self.assertIn("logreg", summary["model_names"])
            self.assertIn("rule_score", summary["model_names"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["calibration_bins_csv_path"]).exists())
            self.assertAlmostEqual(0.2550, float(summary["models"]["logreg"]["brier_score"]), places=4)

    def test_run_calibration_evaluation_rejects_invalid_bin_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            predictions_path = root / "predictions.csv"
            with predictions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "timestamp",
                        "own_mmsi",
                        "target_mmsi",
                        "label_future_conflict",
                        "logreg_score",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-03-09T09:00:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": "440000101",
                        "label_future_conflict": "1",
                        "logreg_score": "0.90",
                    }
                )

            with self.assertRaises(ValueError):
                run_calibration_evaluation(predictions_csv_path=predictions_path, output_prefix=root / "cal", num_bins=1)


if __name__ == "__main__":
    unittest.main()
