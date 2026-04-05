from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.sweep_compare import compare_study_sweep_summaries


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SweepCompareTest(unittest.TestCase):
    def test_compare_study_sweep_summaries_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            focus_summary = root / "focus_summary.json"
            baseline_summary = root / "baseline_summary.json"

            _write_json(
                focus_summary,
                {
                    "status": "completed",
                    "own_ship_case_eval_mmsis": ["440000102"],
                    "rows": [
                        {
                            "modelset_key": "rule_score+logreg+hgbt",
                            "status": "completed",
                            "best_benchmark_f1": 0.66,
                            "best_loo_f1_mean": 0.84,
                            "best_case_f1_mean": 0.97,
                            "best_case_f1_std": 0.01,
                            "best_case_f1_ci95_width": 0.04,
                            "best_case_f1_std_repeat_mean": 0.03,
                            "best_calibration_ece": 0.14,
                        },
                        {
                            "modelset_key": "rule_score+logreg+hgbt+torch_mlp",
                            "status": "completed",
                            "best_benchmark_f1": 0.67,
                            "best_loo_f1_mean": 0.86,
                            "best_case_f1_mean": 0.98,
                            "best_case_f1_std": 0.02,
                            "best_case_f1_ci95_width": 0.05,
                            "best_case_f1_std_repeat_mean": 0.04,
                            "best_calibration_ece": 0.16,
                            "benchmark_elapsed_seconds": 1.5,
                            "torch_mlp_elapsed_seconds": 1.2,
                        },
                    ],
                },
            )
            _write_json(
                baseline_summary,
                {
                    "status": "completed",
                    "rows": [
                        {
                            "modelset_key": "rule_score+logreg+hgbt",
                            "status": "completed",
                            "best_benchmark_f1": 0.65,
                            "best_loo_f1_mean": 0.82,
                            "best_case_f1_mean": 0.95,
                            "best_case_f1_std": 0.03,
                            "best_case_f1_ci95_width": 0.08,
                            "best_case_f1_std_repeat_mean": 0.06,
                            "best_calibration_ece": 0.17,
                        }
                    ],
                },
            )

            summary = compare_study_sweep_summaries(
                focus_summary_path=focus_summary,
                baseline_summary_path=baseline_summary,
                output_prefix=root / "compare",
                focus_label="focused_single_own_ship",
                baseline_label="baseline_multi_own_ship",
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["modelset_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_csv_path"]).exists())

            row_map = {item["modelset_key"]: item for item in summary["rows"]}
            row_a = row_map["rule_score+logreg+hgbt"]
            self.assertEqual(7, int(row_a["compared_metric_count"]))
            self.assertEqual(7, int(row_a["focus_better_count"]))
            self.assertEqual("focus_advantage", row_a["judgement"])
            self.assertAlmostEqual(0.02, float(row_a["delta_best_case_f1_mean"]), places=6)
            self.assertAlmostEqual(-0.03, float(row_a["delta_best_case_f1_std_repeat_mean"]), places=6)

            row_b = row_map["rule_score+logreg+hgbt+torch_mlp"]
            self.assertEqual(0, int(row_b["compared_metric_count"]))
            self.assertEqual("insufficient_metrics", row_b["judgement"])

    def test_sweep_compare_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            focus_summary = root / "focus_summary.json"
            baseline_summary = root / "baseline_summary.json"

            _write_json(
                focus_summary,
                {
                    "status": "completed",
                    "rows": [
                        {
                            "modelset_key": "rule_score+logreg+hgbt",
                            "status": "completed",
                            "best_benchmark_f1": 0.66,
                        }
                    ],
                },
            )
            _write_json(
                baseline_summary,
                {
                    "status": "completed",
                    "rows": [
                        {
                            "modelset_key": "rule_score+logreg+hgbt",
                            "status": "completed",
                            "best_benchmark_f1": 0.65,
                        }
                    ],
                },
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.sweep_compare_cli",
                    "--focus-summary",
                    str(focus_summary),
                    "--baseline-summary",
                    str(baseline_summary),
                    "--output-prefix",
                    str(root / "compare_cli"),
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            self.assertTrue((root / "compare_cli_summary.json").exists())
            self.assertTrue((root / "compare_cli_summary.md").exists())
            self.assertTrue((root / "compare_cli_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()

