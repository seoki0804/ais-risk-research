from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.data_algorithm_quality_review import run_data_algorithm_quality_review


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class DataAlgorithmQualityReviewTest(unittest.TestCase):
    def test_generates_scorecard_todo_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            aggregate_csv = root / "aggregate.csv"
            out_of_time_csv = root / "out_of_time.csv"
            transfer_csv = root / "transfer.csv"
            oot_policy_compare_json = root / "oot_policy_compare.json"
            oot_policy_detail_csv = root / "oot_policy_compare_detail.csv"
            governance_bridge_json = root / "governance_bridge.json"
            governance_bridge_detail_csv = root / "governance_bridge_detail.csv"
            output_prefix = root / "quality_review"

            _write_csv(
                recommendation_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "model_family": "tabular",
                        "f1_mean": 0.82,
                        "f1_std": 0.00,
                        "ece_mean": 0.02,
                    },
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "hgbt",
                        "model_family": "tabular",
                        "f1_mean": 0.60,
                        "f1_std": 0.00,
                        "ece_mean": 0.03,
                    },
                ],
            )
            _write_csv(
                aggregate_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "model_family": "tabular",
                        "f1_mean": 0.82,
                        "f1_std": 0.00,
                        "ece_mean": 0.02,
                        "positive_count_mean": 40,
                    },
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "hgbt",
                        "model_family": "tabular",
                        "f1_mean": 0.60,
                        "f1_std": 0.00,
                        "ece_mean": 0.03,
                        "positive_count_mean": 50,
                    },
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "cnn_weighted",
                        "model_family": "regional_raster_cnn",
                        "f1_mean": 0.44,
                        "f1_std": 0.05,
                        "ece_mean": 0.20,
                        "positive_count_mean": 50,
                    },
                ],
            )
            _write_csv(
                out_of_time_csv,
                [
                    {
                        "region": "houston",
                        "dataset": "houston_pooled_pairwise",
                        "recommended_model": "hgbt",
                        "delta_f1": -0.10,
                        "out_of_time_ece": 0.03,
                        "baseline_positive_count": 40,
                    },
                    {
                        "region": "nola",
                        "dataset": "nola_pooled_pairwise",
                        "recommended_model": "hgbt",
                        "delta_f1": 0.12,
                        "out_of_time_ece": 0.02,
                        "baseline_positive_count": 50,
                    },
                ],
            )
            _write_csv(
                oot_policy_detail_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "policy": "fixed_baseline_threshold",
                        "status": "completed",
                        "delta_f1": -0.02,
                    },
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_name": "hgbt",
                        "policy": "fixed_baseline_threshold",
                        "status": "completed",
                        "delta_f1": 0.12,
                    },
                ],
            )
            oot_policy_compare_json.write_text(
                json.dumps(
                    {
                        "recommended_policy_excluding_oracle": "fixed_baseline_threshold",
                        "detail_csv_path": str(oot_policy_detail_csv),
                    }
                ),
                encoding="utf-8",
            )
            _write_csv(
                transfer_csv,
                [
                    {
                        "source_region": "houston",
                        "target_region": "nola",
                        "recommended_model": "hgbt",
                        "delta_f1": -0.14,
                        "target_ece": 0.03,
                    },
                    {
                        "source_region": "houston",
                        "target_region": "seattle",
                        "recommended_model": "hgbt",
                        "delta_f1": -0.21,
                        "target_ece": 0.04,
                    },
                    {
                        "source_region": "nola",
                        "target_region": "houston",
                        "recommended_model": "hgbt",
                        "delta_f1": 0.12,
                        "target_ece": 0.02,
                    },
                    {
                        "source_region": "nola",
                        "target_region": "seattle",
                        "recommended_model": "hgbt",
                        "delta_f1": 0.08,
                        "target_ece": 0.03,
                    },
                ],
            )
            _write_csv(
                governance_bridge_detail_csv,
                [
                    {
                        "source_region": "houston",
                        "baseline_recommended_model": "hgbt",
                        "baseline_combined_pass": False,
                        "baseline_negative_pairs": 2,
                        "baseline_max_target_ece": 0.04,
                        "governance_mode": "transfer_override_locked",
                        "governed_model": "rule_score",
                        "governed_calibration_method": "isotonic",
                        "governed_combined_pass": True,
                        "governed_negative_pairs": 0,
                        "governed_max_target_ece": 0.07,
                        "notes": "override",
                    },
                    {
                        "source_region": "nola",
                        "baseline_recommended_model": "hgbt",
                        "baseline_combined_pass": True,
                        "baseline_negative_pairs": 0,
                        "baseline_max_target_ece": 0.03,
                        "governance_mode": "baseline_recommended",
                        "governed_model": "hgbt",
                        "governed_calibration_method": "",
                        "governed_combined_pass": True,
                        "governed_negative_pairs": 0,
                        "governed_max_target_ece": 0.03,
                        "notes": "",
                    },
                ],
            )
            governance_bridge_json.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "source_count": 2,
                        "baseline_combined_pass_count": 1,
                        "governed_combined_pass_count": 2,
                        "improved_source_count": 1,
                        "detail_csv_path": str(governance_bridge_detail_csv),
                    }
                ),
                encoding="utf-8",
            )

            summary = run_data_algorithm_quality_review(
                recommendation_csv_path=recommendation_csv,
                aggregate_csv_path=aggregate_csv,
                out_of_time_csv_path=out_of_time_csv,
                transfer_csv_path=transfer_csv,
                output_prefix=output_prefix,
                multisource_transfer_governance_bridge_json_path=governance_bridge_json,
                out_of_time_threshold_policy_compare_json_path=oot_policy_compare_json,
                min_positive_support=30,
                max_ece=0.10,
                max_f1_std=0.03,
                min_out_of_time_delta_f1=-0.05,
                max_negative_transfer_pairs=1,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, int(summary["dataset_count"]))
            self.assertEqual(1, int(summary["baseline_combined_pass_count"]))
            self.assertEqual(2, int(summary["final_combined_pass_count"]))
            self.assertEqual(1, int(summary["governance_improved_dataset_count"]))
            self.assertGreaterEqual(int(summary["high_risk_model_count"]), 1)
            self.assertGreaterEqual(int(summary["todo_count"]), 1)

            md_text = Path(summary["summary_md_path"]).read_text(encoding="utf-8")
            self.assertIn("Data & Algorithm Quality Review", md_text)
            self.assertIn("Detailed To-Do", md_text)

            json_payload = json.loads(Path(summary["summary_json_path"]).read_text(encoding="utf-8"))
            self.assertTrue(json_payload["governance_bridge_used"])
            self.assertEqual(1, int(json_payload["governance_improved_dataset_count"]))

            self.assertTrue(Path(summary["dataset_scorecard_csv_path"]).exists())
            self.assertTrue(Path(summary["high_risk_models_csv_path"]).exists())
            self.assertTrue(Path(summary["todo_csv_path"]).exists())


if __name__ == "__main__":
    unittest.main()
