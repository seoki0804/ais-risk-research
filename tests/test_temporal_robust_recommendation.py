from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.temporal_robust_recommendation import run_temporal_robust_recommendation


class TemporalRobustRecommendationTest(unittest.TestCase):
    def test_switches_to_temporal_robust_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline_aggregate_csv = root / "baseline_aggregate.csv"
            oot_aggregate_csv = root / "oot_aggregate.csv"
            baseline_recommendation_csv = root / "baseline_recommendation.csv"

            with baseline_aggregate_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "dataset",
                        "model_family",
                        "model_name",
                        "f1_mean",
                        "f1_std",
                        "ece_mean",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "dataset": "houston_pooled_pairwise",
                            "model_family": "tabular",
                            "model_name": "hgbt",
                            "f1_mean": "0.83",
                            "f1_std": "0.01",
                            "ece_mean": "0.02",
                        },
                        {
                            "dataset": "houston_pooled_pairwise",
                            "model_family": "tabular",
                            "model_name": "extra_trees",
                            "f1_mean": "0.82",
                            "f1_std": "0.02",
                            "ece_mean": "0.03",
                        },
                        {
                            "dataset": "nola_pooled_pairwise",
                            "model_family": "tabular",
                            "model_name": "hgbt",
                            "f1_mean": "0.60",
                            "f1_std": "0.01",
                            "ece_mean": "0.02",
                        },
                    ]
                )

            with oot_aggregate_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["dataset", "model_name", "f1_mean", "ece_mean"],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "dataset": "houston_pooled_pairwise",
                            "model_name": "hgbt",
                            "f1_mean": "0.70",
                            "ece_mean": "0.03",
                        },
                        {
                            "dataset": "houston_pooled_pairwise",
                            "model_name": "extra_trees",
                            "f1_mean": "0.78",
                            "ece_mean": "0.04",
                        },
                    ]
                )

            with baseline_recommendation_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset", "model_name"])
                writer.writeheader()
                writer.writerow({"dataset": "houston_pooled_pairwise", "model_name": "hgbt"})

            summary = run_temporal_robust_recommendation(
                baseline_aggregate_csv_path=baseline_aggregate_csv,
                out_of_time_aggregate_csv_path=oot_aggregate_csv,
                baseline_recommendation_csv_path=baseline_recommendation_csv,
                output_prefix=root / "temporal_robust",
                dataset_prefix_filters=["houston"],
                f1_tolerance=0.01,
                max_ece_mean=0.10,
                min_out_of_time_delta_f1=-0.05,
                delta_penalty_weight=1.0,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, int(summary["dataset_count"]))
            self.assertEqual(1, int(summary["changed_recommendation_count"]))
            self.assertEqual(0, int(summary["current_temporal_target_pass_count"]))
            self.assertEqual(1, int(summary["robust_temporal_target_pass_count"]))

            rows = list(csv.DictReader(Path(summary["comparison_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(1, len(rows))
            self.assertEqual("hgbt", rows[0]["current_model_name"])
            self.assertEqual("extra_trees", rows[0]["robust_model_name"])
            self.assertEqual("True", rows[0]["changed"])


if __name__ == "__main__":
    unittest.main()
