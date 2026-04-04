from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.transfer_recommendation_eval import run_cross_region_transfer_recommendation_check


class TransferRecommendationEvalTest(unittest.TestCase):
    def test_transfer_recommendation_check_builds_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_csv = root / "houston_pooled_pairwise.csv"
            target_csv = root / "nola_pooled_pairwise.csv"
            source_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")
            target_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            recommendation_csv = root / "recommendation.csv"
            with recommendation_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset", "model_name"])
                writer.writeheader()
                writer.writerow({"dataset": "houston_pooled_pairwise", "model_name": "hgbt"})
                writer.writerow({"dataset": "nola_pooled_pairwise", "model_name": "hgbt"})

            def fake_transfer(**kwargs: object) -> dict[str, object]:
                out_prefix = Path(kwargs["output_prefix"])
                out_prefix.parent.mkdir(parents=True, exist_ok=True)
                target_predictions_csv = out_prefix.with_name(f"{out_prefix.name}_target_predictions.csv")
                with target_predictions_csv.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=["label_future_conflict", "hgbt_score"])
                    writer.writeheader()
                    writer.writerow({"label_future_conflict": "1", "hgbt_score": "0.8"})
                    writer.writerow({"label_future_conflict": "0", "hgbt_score": "0.2"})
                transfer_summary_json = out_prefix.with_name(f"{out_prefix.name}_transfer_summary.json")
                transfer_summary_json.write_text("{}", encoding="utf-8")
                return {
                    "models": {
                        "hgbt": {
                            "status": "completed",
                            "threshold": 0.5,
                            "source_test": {"f1": 0.80, "auroc": 0.95},
                            "target_transfer": {"f1": 0.60, "auroc": 0.85},
                        }
                    },
                    "transfer_summary_json_path": str(transfer_summary_json),
                    "target_predictions_csv_path": str(target_predictions_csv),
                }

            def fake_calibration(**_: object) -> dict[str, object]:
                return {
                    "summary_json_path": str(root / "calibration_summary.json"),
                    "models": {"hgbt": {"ece": 0.09, "brier_score": 0.11}},
                }

            with patch("ais_risk.transfer_recommendation_eval.run_pairwise_transfer_benchmark", side_effect=fake_transfer), patch(
                "ais_risk.transfer_recommendation_eval.run_calibration_evaluation", side_effect=fake_calibration
            ):
                summary = run_cross_region_transfer_recommendation_check(
                    input_paths_by_region={"houston": source_csv, "nola": target_csv},
                    recommendation_csv_path=recommendation_csv,
                    output_root=root / "transfer_out",
                )

            rows = list(csv.DictReader(Path(summary["results_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(2, len(rows))
            for row in rows:
                self.assertEqual("completed", row["status"])
                self.assertEqual("hgbt", row["recommended_model"])
                self.assertAlmostEqual(-0.2, float(row["delta_f1"]), places=8)
                self.assertAlmostEqual(-0.1, float(row["delta_auroc"]), places=8)
                self.assertAlmostEqual(0.09, float(row["target_ece"]), places=8)


if __name__ == "__main__":
    unittest.main()
