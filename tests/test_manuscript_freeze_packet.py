from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.manuscript_freeze_packet import run_manuscript_freeze_packet


class ManuscriptFreezePacketTest(unittest.TestCase):
    def test_builds_freeze_packet_and_operator_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            unseen_csv = root / "unseen_summary.csv"
            threshold_csv = root / "threshold_summary.csv"
            significance_csv = root / "significance.csv"
            recommendation_csv = root / "recommendation.csv"
            aggregate_csv = root / "aggregate.csv"
            output_prefix = root / "freeze_packet"

            with unseen_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "true_area_supported_split_count",
                        "true_area_split_count",
                        "true_area_low_support_count",
                        "low_support_region_splits",
                        "transfer_negative_delta_count",
                        "transfer_row_count",
                        "transfer_region_count",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "true_area_supported_split_count": "8",
                        "true_area_split_count": "8",
                        "true_area_low_support_count": "0",
                        "low_support_region_splits": "",
                        "transfer_negative_delta_count": "1",
                        "transfer_row_count": "6",
                        "transfer_region_count": "3",
                    }
                )

            with threshold_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "dataset",
                        "model_name",
                        "profile",
                        "mean_best_threshold",
                        "mean_recommended_threshold",
                        "mean_regret",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "profile": "balanced",
                        "mean_best_threshold": "0.95",
                        "mean_recommended_threshold": "0.95",
                        "mean_regret": "0.0",
                    }
                )
                writer.writerow(
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "profile": "fp_heavy",
                        "mean_best_threshold": "0.95",
                        "mean_recommended_threshold": "0.95",
                        "mean_regret": "0.0",
                    }
                )
                writer.writerow(
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "hgbt",
                        "profile": "balanced",
                        "mean_best_threshold": "0.95",
                        "mean_recommended_threshold": "0.35",
                        "mean_regret": "16.0",
                    }
                )
                writer.writerow(
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "hgbt",
                        "profile": "fn_heavy",
                        "mean_best_threshold": "0.40",
                        "mean_recommended_threshold": "0.35",
                        "mean_regret": "3.0",
                    }
                )

            with significance_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset", "f1_rec_better_ci", "ece_rec_lower_ci"])
                writer.writeheader()
                writer.writerow({"dataset": "houston_pooled_pairwise", "f1_rec_better_ci": "false", "ece_rec_lower_ci": "true"})
                writer.writerow({"dataset": "nola_pooled_pairwise", "f1_rec_better_ci": "true", "ece_rec_lower_ci": "true"})

            with recommendation_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["dataset", "model_name", "f1_mean", "f1_std", "ece_mean"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "f1_mean": "0.82",
                        "f1_std": "0.01",
                        "ece_mean": "0.02",
                    }
                )
                writer.writerow(
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "hgbt",
                        "f1_mean": "0.60",
                        "f1_std": "0.02",
                        "ece_mean": "0.03",
                    }
                )

            with aggregate_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["dataset", "model_name", "f1_mean", "f1_std", "ece_mean"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "f1_mean": "0.82",
                        "f1_std": "0.01",
                        "ece_mean": "0.02",
                    }
                )
                writer.writerow(
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "hgbt",
                        "f1_mean": "0.60",
                        "f1_std": "0.02",
                        "ece_mean": "0.03",
                    }
                )
                writer.writerow(
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "torch_mlp",
                        "f1_mean": "0.58",
                        "f1_std": "0.05",
                        "ece_mean": "0.21",
                    }
                )

            summary = run_manuscript_freeze_packet(
                unseen_area_summary_csv_path=unseen_csv,
                threshold_robustness_summary_csv_path=threshold_csv,
                significance_csv_path=significance_csv,
                output_prefix=output_prefix,
                min_test_positive_support=10,
                recommendation_csv_path=recommendation_csv,
                aggregate_csv_path=aggregate_csv,
                max_ece=0.10,
                max_f1_std=0.03,
            )

            self.assertEqual("completed", summary["status"])
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            lock_csv = Path(summary["operator_profile_lock_csv_path"])
            self.assertTrue(lock_csv.exists())
            claim_scope_csv = Path(summary["model_claim_scope_csv_path"])
            self.assertTrue(claim_scope_csv.exists())

            rows = list(csv.DictReader(lock_csv.open("r", encoding="utf-8", newline="")))
            self.assertEqual(2, len(rows))
            by_region = {row["region"]: row for row in rows}
            self.assertEqual("balanced", by_region["houston"]["locked_profile"])
            self.assertEqual("fn_heavy", by_region["nola"]["locked_profile"])
            self.assertIn("test positives >= 10", summary["unseen_claim_text"])
            self.assertTrue(bool(summary["recommended_claim_hygiene_ready"]))
            self.assertIn("Main-text model claims are restricted", str(summary["model_claim_caveat_text"]))


if __name__ == "__main__":
    unittest.main()
