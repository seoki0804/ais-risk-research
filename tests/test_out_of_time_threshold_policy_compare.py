from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.out_of_time_threshold_policy_compare import run_out_of_time_threshold_policy_compare


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class OutOfTimeThresholdPolicyCompareTest(unittest.TestCase):
    def test_generates_policy_compare_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            baseline_csv = root / "baseline_leaderboard.csv"
            oot_root = root / "oot"
            dataset = "houston_pooled_pairwise"
            region = "houston"
            model_name = "hgbt"

            _write_csv(
                recommendation_csv,
                [
                    {
                        "dataset": dataset,
                        "model_name": model_name,
                    }
                ],
            )
            _write_csv(
                baseline_csv,
                [
                    {
                        "dataset": dataset,
                        "model_name": model_name,
                        "threshold": 0.80,
                        "f1": 0.82,
                        "ece": 0.02,
                    },
                    {
                        "dataset": dataset,
                        "model_name": "extra_trees",
                        "threshold": 0.55,
                        "f1": 0.83,
                        "ece": 0.03,
                    },
                ],
            )

            oot_dir = oot_root / region / "timestamp_split"
            _write_csv(
                oot_dir / f"{dataset}_all_models_leaderboard.csv",
                [
                    {
                        "dataset": dataset,
                        "model_name": model_name,
                        "status": "completed",
                        "threshold": 0.40,
                        "f1": 0.66,
                        "ece": 0.03,
                    }
                ],
            )
            _write_csv(
                oot_dir / f"{dataset}_tabular_all_models_test_predictions.csv",
                [
                    {
                        "timestamp": "2023-01-01T00:00:00Z",
                        "own_mmsi": "111",
                        "target_mmsi": "211",
                        "label_future_conflict": 1,
                        "hgbt_score": 0.90,
                    },
                    {
                        "timestamp": "2023-01-01T00:01:00Z",
                        "own_mmsi": "112",
                        "target_mmsi": "212",
                        "label_future_conflict": 1,
                        "hgbt_score": 0.80,
                    },
                    {
                        "timestamp": "2023-01-01T00:02:00Z",
                        "own_mmsi": "113",
                        "target_mmsi": "213",
                        "label_future_conflict": 0,
                        "hgbt_score": 0.70,
                    },
                    {
                        "timestamp": "2023-01-01T00:03:00Z",
                        "own_mmsi": "114",
                        "target_mmsi": "214",
                        "label_future_conflict": 0,
                        "hgbt_score": 0.20,
                    },
                    {
                        "timestamp": "2023-01-01T00:04:00Z",
                        "own_mmsi": "115",
                        "target_mmsi": "215",
                        "label_future_conflict": 1,
                        "hgbt_score": 0.10,
                    },
                    {
                        "timestamp": "2023-01-01T00:05:00Z",
                        "own_mmsi": "116",
                        "target_mmsi": "216",
                        "label_future_conflict": 0,
                        "hgbt_score": 0.05,
                    },
                ],
            )

            summary = run_out_of_time_threshold_policy_compare(
                recommendation_csv_path=recommendation_csv,
                baseline_leaderboard_csv_path=baseline_csv,
                out_of_time_output_root=oot_root,
                output_prefix=root / "oot_policy_compare",
                threshold_grid_step=0.01,
                max_out_of_time_ece=0.10,
                min_out_of_time_delta_f1=-0.05,
                max_in_time_regression_from_best_f1=0.02,
                include_oracle_policy=True,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(3, int(summary["detail_row_count"]))
            self.assertEqual(3, int(summary["policy_row_count"]))
            self.assertEqual("fixed_baseline_threshold", summary["recommended_policy_excluding_oracle"])
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["detail_csv_path"]).exists())
            self.assertTrue(Path(summary["policy_summary_csv_path"]).exists())

            fixed_rows = [
                row
                for row in summary["houston_rows"]
                if str(row.get("policy")) == "fixed_baseline_threshold" and str(row.get("status")) == "completed"
            ]
            self.assertEqual(1, len(fixed_rows))
            self.assertTrue(bool(fixed_rows[0].get("combined_pass")))


if __name__ == "__main__":
    unittest.main()
