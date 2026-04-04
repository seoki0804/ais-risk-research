from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.out_of_time_eval import run_out_of_time_recommendation_check


class OutOfTimeEvalTest(unittest.TestCase):
    def test_out_of_time_recommendation_check_builds_delta_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "houston_pooled_pairwise.csv"
            input_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            recommendation_csv = root / "recommendation.csv"
            with recommendation_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset", "model_name"])
                writer.writeheader()
                writer.writerow({"dataset": "houston_pooled_pairwise", "model_name": "hgbt"})

            baseline_csv = root / "baseline.csv"
            with baseline_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["dataset", "model_name", "status", "f1", "auroc", "ece", "positive_count"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "status": "completed",
                        "f1": "0.80",
                        "auroc": "0.95",
                        "ece": "0.03",
                        "positive_count": "40",
                    }
                )

            def fake_run_all_supported_models(**_: object) -> dict[str, object]:
                out = root / "run"
                out.mkdir(exist_ok=True)
                leaderboard_csv = out / "leaderboard.csv"
                with leaderboard_csv.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=["dataset", "model_name", "status", "f1", "auroc", "ece", "positive_count", "notes"],
                    )
                    writer.writeheader()
                    writer.writerow(
                        {
                            "dataset": "houston_pooled_pairwise",
                            "model_name": "hgbt",
                            "status": "completed",
                            "f1": "0.72",
                            "auroc": "0.90",
                            "ece": "0.05",
                            "positive_count": "22",
                            "notes": "",
                        }
                    )
                return {
                    "leaderboard_csv_path": str(leaderboard_csv),
                    "summary_json_path": str(out / "summary.json"),
                }

            with patch("ais_risk.out_of_time_eval.run_all_supported_models", side_effect=fake_run_all_supported_models):
                summary = run_out_of_time_recommendation_check(
                    input_paths_by_region={"houston": input_csv},
                    recommendation_csv_path=recommendation_csv,
                    baseline_leaderboard_csv_path=baseline_csv,
                    output_root=root / "oot",
                )

            result_rows = list(csv.DictReader(Path(summary["results_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(1, len(result_rows))
            row = result_rows[0]
            self.assertEqual("completed", row["status"])
            self.assertAlmostEqual(-0.08, float(row["delta_f1"]), places=8)
            self.assertAlmostEqual(-0.05, float(row["delta_auroc"]), places=8)
            self.assertAlmostEqual(0.02, float(row["delta_ece"]), places=8)


if __name__ == "__main__":
    unittest.main()
