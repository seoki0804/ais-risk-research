from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.focus_compare import run_focus_vs_baseline_sweep_bundle


class FocusCompareTest(unittest.TestCase):
    def test_run_focus_vs_baseline_sweep_bundle_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_compare_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Compare Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_focus_vs_baseline_sweep_bundle(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_compare",
                focus_own_ship_case_eval_mmsis=["440000102"],
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
                build_study_journals=True,
                study_journal_output_template=str(root / "journals" / "{date}_{dataset_id}_{modelset_index}_{sweep_type}.md"),
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, int(summary["focus_modelset_count"]))
            self.assertEqual(1, int(summary["baseline_modelset_count"]))
            self.assertEqual(1, int(summary["compared_modelset_count"]))
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["compare_summary_md_path"]).exists())
            compare_text = Path(str(summary["compare_summary_md_path"])).read_text(encoding="utf-8")
            self.assertIn("rule_score+logreg", compare_text)
            self.assertIn("Judgement", compare_text)

    def test_run_focus_vs_baseline_sweep_bundle_can_auto_select_focus_mmsi(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_compare_auto_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Compare Auto Area |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_focus_vs_baseline_sweep_bundle(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_compare_auto",
                focus_own_ship_case_eval_mmsis=None,
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
                auto_focus_own_ship=True,
                auto_focus_rank=1,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual("auto_top_candidate", summary["focus_mmsi_resolution_mode"])
            self.assertEqual(["440000102"], summary["focus_own_ship_case_eval_mmsis"])
            self.assertTrue(Path(str(summary["focus_mmsi_auto_workflow_summary_json_path"])).exists())

    def test_run_focus_vs_baseline_sweep_bundle_can_reuse_baseline_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_compare_reuse_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Compare Reuse Area |",
                    ]
                ),
                encoding="utf-8",
            )

            first = run_focus_vs_baseline_sweep_bundle(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_compare_first",
                focus_own_ship_case_eval_mmsis=["440000102"],
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs_first",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
            )

            second = run_focus_vs_baseline_sweep_bundle(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_compare_second",
                focus_own_ship_case_eval_mmsis=["440000103"],
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs_second",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
                baseline_sweep_summary_json_path=first["baseline_sweep_summary_json_path"],
            )

            self.assertEqual("completed", second["status"])
            self.assertTrue(bool(second["baseline_reused"]))
            self.assertEqual(
                str(first["baseline_sweep_summary_json_path"]),
                str(second["baseline_sweep_summary_json_path"]),
            )
            self.assertEqual(
                str(first["baseline_sweep_summary_json_path"]),
                str(second["baseline_reuse_source_summary_json_path"]),
            )

    def test_focus_compare_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_compare_cli_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Compare CLI Area |",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.focus_compare_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-prefix",
                    str(root / "focus_compare_cli"),
                    "--output-root",
                    str(root / "outputs"),
                    "--focus-own-ship-case-eval-mmsis",
                    "440000102",
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
            self.assertTrue((root / "focus_compare_cli_summary.json").exists())
            self.assertTrue((root / "focus_compare_cli_summary.md").exists())
            self.assertTrue((root / "focus_compare_cli_compare_summary.md").exists())

    def test_focus_compare_cli_can_auto_select_focus_mmsi(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_compare_cli_auto_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Compare CLI Auto Area |",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.focus_compare_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-prefix",
                    str(root / "focus_compare_cli_auto"),
                    "--output-root",
                    str(root / "outputs"),
                    "--auto-focus-own-ship",
                    "--auto-focus-rank",
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
            summary_json = root / "focus_compare_cli_auto_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual("auto_top_candidate", payload["focus_mmsi_resolution_mode"])
            self.assertEqual(["440000102"], payload["focus_own_ship_case_eval_mmsis"])


if __name__ == "__main__":
    unittest.main()
