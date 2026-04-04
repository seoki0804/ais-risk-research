from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.reliability_report import run_reliability_report_for_recommended_models


class ReliabilityReportTest(unittest.TestCase):
    def test_reliability_report_generates_region_summary_and_figure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            run_manifest_csv = root / "manifest.csv"

            with recommendation_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset", "model_name"])
                writer.writeheader()
                writer.writerow({"dataset": "houston_pooled_pairwise", "model_name": "hgbt"})

            run_dir = root / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            leaderboard_csv = run_dir / "leaderboard.csv"
            predictions_csv = run_dir / "pred.csv"

            with leaderboard_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["dataset", "model_name", "status", "predictions_csv_path"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "status": "completed",
                        "predictions_csv_path": str(predictions_csv),
                    }
                )

            with predictions_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["label_future_conflict", "hgbt_score"])
                writer.writeheader()
                writer.writerow({"label_future_conflict": "1", "hgbt_score": "0.90"})
                writer.writerow({"label_future_conflict": "0", "hgbt_score": "0.10"})
                writer.writerow({"label_future_conflict": "1", "hgbt_score": "0.70"})
                writer.writerow({"label_future_conflict": "0", "hgbt_score": "0.20"})

            with run_manifest_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["region", "seed", "leaderboard_csv_path"])
                writer.writeheader()
                writer.writerow({"region": "houston", "seed": "41", "leaderboard_csv_path": str(leaderboard_csv)})

            summary = run_reliability_report_for_recommended_models(
                recommendation_csv_path=recommendation_csv,
                run_manifest_csv_path=run_manifest_csv,
                output_root=root / "out",
                num_bins=5,
            )

            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["region_summary_csv_path"]).exists())
            self.assertTrue(Path(summary["region_bins_csv_path"]).exists())

            region_rows = list(csv.DictReader(Path(summary["region_summary_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(1, len(region_rows))
            self.assertEqual("houston", region_rows[0]["region"])
            self.assertEqual("hgbt", region_rows[0]["model_name"])
            self.assertTrue(Path(region_rows[0]["figure_path"]).exists())


if __name__ == "__main__":
    unittest.main()
