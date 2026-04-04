from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.error_taxonomy_report import run_error_taxonomy_for_recommended_models


class ErrorTaxonomyReportTest(unittest.TestCase):
    def test_error_taxonomy_report_generates_summary_and_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "houston_pooled_pairwise.csv"
            recommendation_csv = root / "recommendation.csv"
            run_manifest_csv = root / "manifest.csv"
            leaderboard_csv = root / "leaderboard.csv"
            predictions_csv = root / "predictions.csv"

            with input_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "timestamp",
                        "own_mmsi",
                        "target_mmsi",
                        "encounter_type",
                        "own_vessel_type",
                        "target_vessel_type",
                        "distance_nm",
                        "tcpa_min",
                        "label_future_conflict",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-01-01T00:00:00Z",
                        "own_mmsi": "1",
                        "target_mmsi": "11",
                        "encounter_type": "crossing",
                        "own_vessel_type": "cargo",
                        "target_vessel_type": "tanker",
                        "distance_nm": "0.4",
                        "tcpa_min": "3.0",
                        "label_future_conflict": "0",
                    }
                )
                writer.writerow(
                    {
                        "timestamp": "2026-01-01T00:01:00Z",
                        "own_mmsi": "1",
                        "target_mmsi": "12",
                        "encounter_type": "head_on",
                        "own_vessel_type": "cargo",
                        "target_vessel_type": "cargo",
                        "distance_nm": "1.2",
                        "tcpa_min": "8.0",
                        "label_future_conflict": "1",
                    }
                )

            with recommendation_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset", "model_name"])
                writer.writeheader()
                writer.writerow({"dataset": "houston_pooled_pairwise", "model_name": "hgbt"})

            with leaderboard_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset", "model_name", "status", "predictions_csv_path"])
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "status": "completed",
                        "predictions_csv_path": str(predictions_csv),
                    }
                )

            with run_manifest_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["region", "seed", "leaderboard_csv_path"])
                writer.writeheader()
                writer.writerow({"region": "houston", "seed": "42", "leaderboard_csv_path": str(leaderboard_csv)})

            with predictions_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["timestamp", "own_mmsi", "target_mmsi", "label_future_conflict", "hgbt_pred"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-01-01T00:00:00Z",
                        "own_mmsi": "1",
                        "target_mmsi": "11",
                        "label_future_conflict": "0",
                        "hgbt_pred": "1",
                    }
                )
                writer.writerow(
                    {
                        "timestamp": "2026-01-01T00:01:00Z",
                        "own_mmsi": "1",
                        "target_mmsi": "12",
                        "label_future_conflict": "1",
                        "hgbt_pred": "0",
                    }
                )

            summary = run_error_taxonomy_for_recommended_models(
                input_paths_by_region={"houston": input_csv},
                recommendation_csv_path=recommendation_csv,
                run_manifest_csv_path=run_manifest_csv,
                output_root=root / "out",
                seed=42,
            )

            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_csv_path"]).exists())
            self.assertTrue(Path(summary["taxonomy_csv_path"]).exists())

            summary_rows = list(csv.DictReader(Path(summary["summary_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(1, len(summary_rows))
            self.assertEqual("1", summary_rows[0]["fp"])
            self.assertEqual("1", summary_rows[0]["fn"])

            detail_rows = list(csv.DictReader(Path(summary["taxonomy_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertTrue(any(row["error_type"] == "fp" for row in detail_rows))
            self.assertTrue(any(row["error_type"] == "fn" for row in detail_rows))


if __name__ == "__main__":
    unittest.main()
