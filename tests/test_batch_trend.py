from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.batch_trend import build_batch_trend_report


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class BatchTrendTest(unittest.TestCase):
    def test_build_batch_trend_report_prioritizes_high_alert_and_worsening(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            # Previous dataset_x snapshots
            _write_text(
                outputs / "dataset_x_prev_validation.json",
                '{"strategies":{"own_ship_loo":{"best_model":{"name":"logreg","f1_mean":0.82}}}}',
            )
            _write_text(
                outputs / "dataset_x_prev_calibration.json",
                '{"models":{"logreg":{"status":"completed","ece":0.10,"brier_score":0.16}}}',
            )
            _write_text(
                outputs / "dataset_x_prev_case.json",
                '{"aggregate_models":{"logreg":{"ship_count":3,"f1_mean":0.74,"f1_std":0.06,"f1_ci95_width":0.16,"auroc_mean":0.80}}}',
            )
            _write_text(
                outputs / "dataset_x_prev_study_summary.json",
                (
                    '{"dataset_id":"dataset_x","pairwise":{"row_count":200,"positive_rate":0.35},'
                    '"pairwise_split_strategy":"own_ship",'
                    f'"validation_suite_summary_json_path":"{outputs / "dataset_x_prev_validation.json"}",'
                    f'"calibration_eval_summary_json_path":"{outputs / "dataset_x_prev_calibration.json"}",'
                    f'"own_ship_case_eval_summary_json_path":"{outputs / "dataset_x_prev_case.json"}"'
                    "}"
                ),
            )

            # Current dataset_x snapshots (worsening)
            _write_text(
                outputs / "dataset_x_cur_validation.json",
                '{"strategies":{"own_ship_loo":{"best_model":{"name":"logreg","f1_mean":0.76}}}}',
            )
            _write_text(
                outputs / "dataset_x_cur_calibration.json",
                '{"models":{"logreg":{"status":"completed","ece":0.19,"brier_score":0.25}}}',
            )
            _write_text(
                outputs / "dataset_x_cur_case.json",
                '{"aggregate_models":{"logreg":{"ship_count":3,"f1_mean":0.69,"f1_std":0.11,"f1_ci95_width":0.24,"auroc_mean":0.75}}}',
            )
            _write_text(
                outputs / "dataset_x_cur_study_summary.json",
                (
                    '{"dataset_id":"dataset_x","pairwise":{"row_count":220,"positive_rate":0.36},'
                    '"pairwise_split_strategy":"own_ship",'
                    f'"validation_suite_summary_json_path":"{outputs / "dataset_x_cur_validation.json"}",'
                    f'"calibration_eval_summary_json_path":"{outputs / "dataset_x_cur_calibration.json"}",'
                    f'"own_ship_case_eval_summary_json_path":"{outputs / "dataset_x_cur_case.json"}"'
                    "}"
                ),
            )

            # Current dataset_y snapshots (new high alert)
            _write_text(
                outputs / "dataset_y_cur_validation.json",
                '{"strategies":{"own_ship_loo":{"best_model":{"name":"logreg","f1_mean":0.70}}}}',
            )
            _write_text(
                outputs / "dataset_y_cur_calibration.json",
                '{"models":{"logreg":{"status":"completed","ece":0.24,"brier_score":0.30}}}',
            )
            _write_text(
                outputs / "dataset_y_cur_case.json",
                '{"aggregate_models":{"logreg":{"ship_count":4,"f1_mean":0.67,"f1_std":0.14,"f1_ci95_width":0.30,"auroc_mean":0.74}}}',
            )
            _write_text(
                outputs / "dataset_y_cur_study_summary.json",
                (
                    '{"dataset_id":"dataset_y","pairwise":{"row_count":180,"positive_rate":0.40},'
                    '"pairwise_split_strategy":"own_ship",'
                    f'"validation_suite_summary_json_path":"{outputs / "dataset_y_cur_validation.json"}",'
                    f'"calibration_eval_summary_json_path":"{outputs / "dataset_y_cur_calibration.json"}",'
                    f'"own_ship_case_eval_summary_json_path":"{outputs / "dataset_y_cur_case.json"}"'
                    "}"
                ),
            )

            _write_text(
                outputs / "study_batch_prev_summary.json",
                json.dumps(
                    {
                        "manifest_glob": "data/manifests/*.md",
                        "total_manifests": 1,
                        "completed_count": 1,
                        "failed_count": 0,
                        "items": [
                            {
                                "dataset_id": "dataset_x",
                                "status": "completed",
                                "study_summary_json_path": str(outputs / "dataset_x_prev_study_summary.json"),
                            }
                        ],
                    }
                ),
            )
            _write_text(
                outputs / "study_batch_cur_summary.json",
                json.dumps(
                    {
                        "manifest_glob": "data/manifests/*.md",
                        "total_manifests": 2,
                        "completed_count": 2,
                        "failed_count": 0,
                        "items": [
                            {
                                "dataset_id": "dataset_x",
                                "status": "completed",
                                "study_summary_json_path": str(outputs / "dataset_x_cur_study_summary.json"),
                            },
                            {
                                "dataset_id": "dataset_y",
                                "status": "completed",
                                "study_summary_json_path": str(outputs / "dataset_y_cur_study_summary.json"),
                            },
                        ],
                    }
                ),
            )

            summary = build_batch_trend_report(
                output_prefix=outputs / "batch_trend",
                history_batch_summary_glob=str(outputs / "study_batch_*_summary.json"),
                current_batch_summary_path=outputs / "study_batch_cur_summary.json",
                max_history=5,
                moving_average_window=2,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["history_count"])
            self.assertEqual(2, summary["dataset_count"])
            self.assertGreaterEqual(summary["priority_dataset_count"], 2)
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["dataset_trends_csv_path"]).exists())

            dataset_rows = {row["dataset_id"]: row for row in summary["dataset_rows"]}
            self.assertAlmostEqual(0.79, float(dataset_rows["dataset_x"]["moving_avg_own_ship_loo_f1_mean"]), places=4)
            self.assertAlmostEqual(0.145, float(dataset_rows["dataset_x"]["moving_avg_best_calibration_ece"]), places=4)
            self.assertAlmostEqual(0.085, float(dataset_rows["dataset_x"]["moving_avg_best_own_ship_case_f1_std"]), places=4)
            self.assertAlmostEqual(0.20, float(dataset_rows["dataset_x"]["moving_avg_best_own_ship_case_f1_ci95_width"]), places=4)
            self.assertAlmostEqual(-0.03, float(dataset_rows["dataset_x"]["delta_vs_mavg_own_ship_loo_f1_mean"]), places=4)
            self.assertAlmostEqual(0.045, float(dataset_rows["dataset_x"]["delta_vs_mavg_best_calibration_ece"]), places=4)
            self.assertAlmostEqual(0.025, float(dataset_rows["dataset_x"]["delta_vs_mavg_best_own_ship_case_f1_std"]), places=4)
            self.assertAlmostEqual(0.04, float(dataset_rows["dataset_x"]["delta_vs_mavg_best_own_ship_case_f1_ci95_width"]), places=4)
            self.assertAlmostEqual(7.0, float(dataset_rows["dataset_x"]["mavg_deviation_score"]), places=4)
            self.assertEqual(4, int(dataset_rows["dataset_x"]["mavg_deviation_break_count"]))
            self.assertEqual(0.0, float(dataset_rows["dataset_y"]["mavg_deviation_score"]))
            self.assertEqual(0, int(dataset_rows["dataset_y"]["mavg_deviation_break_count"]))

            top_rows = summary["top_mavg_deviation_rows"]
            self.assertEqual("dataset_x", top_rows[0]["dataset_id"])
            self.assertAlmostEqual(7.0, float(top_rows[0]["mavg_deviation_score"]), places=4)
            self.assertEqual(4, int(top_rows[0]["mavg_deviation_break_count"]))

            with Path(summary["dataset_trends_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
                rows = {row["dataset_id"]: row for row in csv.DictReader(handle)}
            self.assertIn("dataset_x", rows)
            self.assertIn("dataset_y", rows)
            self.assertEqual("True", rows["dataset_x"]["worsening"])
            self.assertEqual("True", rows["dataset_y"]["priority"])
            self.assertIn("mavg_deviation_score", rows["dataset_x"])
            self.assertIn("mavg_deviation_break_count", rows["dataset_x"])

            report_text = Path(summary["summary_md_path"]).read_text(encoding="utf-8")
            self.assertIn("## Top Moving-Average Deviation (Top 3, Risk Direction)", report_text)
            self.assertIn("| 1 | dataset_x | 7.0000 | 4 |", report_text)

    def test_batch_trend_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)
            _write_text(
                outputs / "study_batch_single_summary.json",
                '{"manifest_glob":"data/manifests/*.md","total_manifests":0,"completed_count":0,"failed_count":0,"items":[]}',
            )
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.batch_trend_cli",
                    "--output-prefix",
                    str(outputs / "batch_trend_cli"),
                    "--history-batch-summary-glob",
                    str(outputs / "study_batch_*_summary.json"),
                    "--max-history",
                    "3",
                    "--moving-average-window",
                    "2",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)


if __name__ == "__main__":
    unittest.main()
