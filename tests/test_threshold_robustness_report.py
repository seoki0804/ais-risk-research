from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.threshold_robustness_report import run_threshold_robustness_report


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class ThresholdRobustnessReportTest(unittest.TestCase):
    def test_generates_detail_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            run_manifest_csv = root / "run_manifest.csv"
            leaderboard_csv = root / "leaderboard.csv"
            predictions_csv = root / "predictions.csv"
            output_prefix = root / "threshold_robustness"

            _write_csv(
                recommendation_csv,
                [
                    {
                        "dataset": "alpha_pooled_pairwise",
                        "model_name": "model_a",
                    }
                ],
            )
            _write_csv(
                run_manifest_csv,
                [
                    {
                        "region": "alpha",
                        "seed": 41,
                        "leaderboard_csv_path": str(leaderboard_csv),
                    },
                    {
                        "region": "alpha",
                        "seed": 42,
                        "leaderboard_csv_path": str(leaderboard_csv),
                    },
                ],
            )
            _write_csv(
                leaderboard_csv,
                [
                    {
                        "dataset": "alpha_pooled_pairwise",
                        "model_name": "model_a",
                        "status": "completed",
                        "threshold": 0.5,
                        "predictions_csv_path": str(predictions_csv),
                    }
                ],
            )
            _write_csv(
                predictions_csv,
                [
                    {"label_future_conflict": 1, "model_a_score": 0.9},
                    {"label_future_conflict": 1, "model_a_score": 0.8},
                    {"label_future_conflict": 0, "model_a_score": 0.7},
                    {"label_future_conflict": 0, "model_a_score": 0.2},
                ],
            )

            summary = run_threshold_robustness_report(
                recommendation_csv_path=recommendation_csv,
                run_manifest_csv_path=run_manifest_csv,
                output_prefix=output_prefix,
                threshold_grid=[0.3, 0.5, 0.7],
                cost_profiles="balanced:1:1,fn_heavy:1:3",
            )

            self.assertEqual("completed", summary["status"])
            self.assertTrue(Path(summary["detail_csv_path"]).exists())
            self.assertTrue(Path(summary["summary_csv_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())

            detail_rows = list(csv.DictReader(Path(summary["detail_csv_path"]).open("r", encoding="utf-8", newline="")))
            summary_rows = list(csv.DictReader(Path(summary["summary_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(4, len(detail_rows))
            self.assertEqual(2, len(summary_rows))
            self.assertTrue(all(row["dataset"] == "alpha_pooled_pairwise" for row in summary_rows))

            payload = json.loads(Path(summary["summary_json_path"]).read_text(encoding="utf-8"))
            self.assertEqual(4, payload["row_count_detail"])
            self.assertEqual(2, payload["row_count_summary"])


if __name__ == "__main__":
    unittest.main()
