from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.stratified_eval import run_stratified_evaluation


class StratifiedEvalTest(unittest.TestCase):
    def test_run_stratified_evaluation_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pairwise_path = root / "pairwise.csv"
            predictions_path = root / "predictions.csv"
            output_prefix = root / "stratified_eval"

            pairwise_fields = [
                "timestamp",
                "own_mmsi",
                "target_mmsi",
                "encounter_type",
                "distance_nm",
                "label_future_conflict",
            ]
            with pairwise_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=pairwise_fields)
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "timestamp": "2026-03-09T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000101",
                            "encounter_type": "head_on",
                            "distance_nm": "0.30",
                            "label_future_conflict": "1",
                        },
                        {
                            "timestamp": "2026-03-09T09:01:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000102",
                            "encounter_type": "crossing",
                            "distance_nm": "1.20",
                            "label_future_conflict": "0",
                        },
                        {
                            "timestamp": "2026-03-09T09:02:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000103",
                            "encounter_type": "overtaking",
                            "distance_nm": "3.10",
                            "label_future_conflict": "1",
                        },
                    ]
                )

            prediction_fields = [
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
                writer = csv.DictWriter(handle, fieldnames=prediction_fields)
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "timestamp": "2026-03-09T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000101",
                            "label_future_conflict": "1",
                            "logreg_score": "0.9",
                            "logreg_pred": "1",
                            "rule_score_score": "0.8",
                            "rule_score_pred": "1",
                        },
                        {
                            "timestamp": "2026-03-09T09:01:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000102",
                            "label_future_conflict": "0",
                            "logreg_score": "0.7",
                            "logreg_pred": "1",
                            "rule_score_score": "0.2",
                            "rule_score_pred": "0",
                        },
                        {
                            "timestamp": "2026-03-09T09:02:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000103",
                            "label_future_conflict": "1",
                            "logreg_score": "0.2",
                            "logreg_pred": "0",
                            "rule_score_score": "0.1",
                            "rule_score_pred": "0",
                        },
                    ]
                )

            summary = run_stratified_evaluation(
                pairwise_dataset_csv_path=pairwise_path,
                predictions_csv_path=predictions_path,
                output_prefix=output_prefix,
                model_names=["logreg", "rule_score"],
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(3, summary["joined_row_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["strata_metrics_csv_path"]).exists())


if __name__ == "__main__":
    unittest.main()
