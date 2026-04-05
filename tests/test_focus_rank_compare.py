from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.focus_rank_compare import run_focus_rank_compare_bundle


class FocusRankCompareTest(unittest.TestCase):
    def test_run_focus_rank_compare_bundle_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_rank_compare_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Rank Compare Area |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_focus_rank_compare_bundle(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_rank_compare",
                auto_focus_ranks=[1, 2],
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, int(summary["run_count"]))
            self.assertTrue(bool(summary.get("reuse_baseline_across_ranks", False)))
            self.assertTrue(bool(summary.get("shared_baseline_summary_json_path")))
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["rank_rows_csv_path"]).exists())
            self.assertTrue(Path(summary["modelset_rows_csv_path"]).exists())
            self.assertEqual(1, len(summary.get("best_rank_by_modelset", [])))
            modelset_best = summary["best_rank_by_modelset"][0]
            self.assertEqual("rule_score+logreg", modelset_best["modelset_key"])
            self.assertIn(modelset_best["best_rank"], [1, 2])
            rows = summary.get("rank_rows", [])
            self.assertEqual(2, len(rows))
            self.assertFalse(bool(rows[0].get("baseline_reused", True)))
            self.assertTrue(bool(rows[1].get("baseline_reused", False)))

    def test_focus_rank_compare_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_rank_compare_cli_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Rank Compare CLI Area |",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.focus_rank_compare_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-prefix",
                    str(root / "focus_rank_compare_cli"),
                    "--output-root",
                    str(root / "outputs"),
                    "--auto-focus-ranks",
                    "1",
                    "--benchmark-modelsets",
                    "rule_score,logreg",
                    "--no-run-calibration-eval",
                    "--no-run-own-ship-loo",
                    "--run-own-ship-case-eval",
                    "--own-ship-case-eval-min-rows",
                    "5",
                    "--own-ship-case-eval-repeat-count",
                    "2",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            summary_json = root / "focus_rank_compare_cli_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual([1], payload["auto_focus_ranks"])
            self.assertEqual(1, payload["run_count"])
            self.assertTrue((root / "focus_rank_compare_cli_rank_rows.csv").exists())
            self.assertTrue((root / "focus_rank_compare_cli_modelset_rows.csv").exists())

    def test_run_focus_rank_compare_bundle_can_disable_baseline_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_rank_compare_no_reuse_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Rank Compare No Reuse Area |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_focus_rank_compare_bundle(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_rank_compare_no_reuse",
                auto_focus_ranks=[1, 2],
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
                reuse_baseline_across_ranks=False,
            )
            self.assertEqual("completed", summary["status"])
            self.assertFalse(bool(summary.get("reuse_baseline_across_ranks", True)))
            self.assertEqual("", str(summary.get("shared_baseline_summary_json_path", "")))
            rows = summary.get("rank_rows", [])
            self.assertEqual(2, len(rows))
            self.assertFalse(bool(rows[0].get("baseline_reused", True)))
            self.assertFalse(bool(rows[1].get("baseline_reused", True)))


if __name__ == "__main__":
    unittest.main()
