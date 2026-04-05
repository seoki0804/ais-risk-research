from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.split_conformal_interval import run_split_conformal_interval


class SplitConformalIntervalTest(unittest.TestCase):
    def test_builds_intervals_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            calibration_path = root / "calibration_predictions.csv"
            target_path = root / "target_predictions.csv"
            output_prefix = root / "split_conformal"

            fieldnames = [
                "timestamp",
                "own_mmsi",
                "target_mmsi",
                "label_future_conflict",
                "hgbt_score",
                "hgbt_pred",
            ]
            with calibration_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(
                    [
                        {"timestamp": "t1", "own_mmsi": "1", "target_mmsi": "11", "label_future_conflict": "0", "hgbt_score": "0.10", "hgbt_pred": "0"},
                        {"timestamp": "t2", "own_mmsi": "1", "target_mmsi": "12", "label_future_conflict": "1", "hgbt_score": "0.80", "hgbt_pred": "1"},
                        {"timestamp": "t3", "own_mmsi": "1", "target_mmsi": "13", "label_future_conflict": "1", "hgbt_score": "0.70", "hgbt_pred": "1"},
                        {"timestamp": "t4", "own_mmsi": "1", "target_mmsi": "14", "label_future_conflict": "0", "hgbt_score": "0.20", "hgbt_pred": "0"},
                    ]
                )
            with target_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(
                    [
                        {"timestamp": "u1", "own_mmsi": "2", "target_mmsi": "21", "label_future_conflict": "1", "hgbt_score": "0.75", "hgbt_pred": "1"},
                        {"timestamp": "u2", "own_mmsi": "2", "target_mmsi": "22", "label_future_conflict": "0", "hgbt_score": "0.25", "hgbt_pred": "0"},
                    ]
                )

            summary = run_split_conformal_interval(
                calibration_predictions_csv_path=calibration_path,
                target_predictions_csv_path=target_path,
                output_prefix=output_prefix,
                model_names=["hgbt"],
                miscoverage_alpha=0.1,
            )

            self.assertEqual("completed", summary["status"])
            self.assertTrue((root / "split_conformal_summary.json").exists())
            self.assertTrue((root / "split_conformal_intervals.csv").exists())
            metrics = summary["models"]["hgbt"]
            self.assertEqual(2, metrics["sample_count"])
            self.assertGreaterEqual(metrics["qhat"], 0.0)
            self.assertGreaterEqual(metrics["mean_interval_width"], 0.0)


if __name__ == "__main__":
    unittest.main()
