from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.focus_seed_pipeline import _resolve_auto_select_workflow_output_dir, run_focus_seed_pipeline


class FocusSeedPipelineTest(unittest.TestCase):
    def test_resolve_auto_select_workflow_output_dir_uses_unique_prefix_path_for_default(self) -> None:
        prefix = Path("/tmp/focus_seed_pipeline_case")
        resolved = _resolve_auto_select_workflow_output_dir(
            prefix=prefix,
            auto_select_workflow_output_dir="outputs/focus_seed_pipeline/auto_focus_workflow",
        )
        self.assertEqual(Path("/tmp/focus_seed_pipeline_case_auto_focus_workflow"), resolved)

    def test_run_focus_seed_pipeline_auto_select_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_seed_pipeline_auto_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Seed Pipeline Auto Area |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_focus_seed_pipeline(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_seed_pipeline_auto",
                benchmark_modelsets=[["rule_score", "logreg"]],
                seed_values=[42],
                auto_select_focus_mmsis=True,
                auto_select_count=2,
                auto_select_start_rank=1,
                auto_select_workflow_output_dir=root / "auto_focus_workflow",
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
                torch_device="cpu",
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual("auto_candidates", summary["focus_mmsi_resolution_mode"])
            self.assertGreaterEqual(len(summary.get("focus_own_ship_mmsis", [])), 1)
            self.assertLessEqual(len(summary.get("focus_own_ship_mmsis", [])), 2)
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["selected_focus_mmsis_csv_path"]).exists())
            self.assertTrue(Path(summary["focus_seed_compare_summary_json_path"]).exists())
            self.assertTrue(Path(summary["focus_seed_compare_summary_md_path"]).exists())
            self.assertTrue(Path(summary["validation_gate_rows_csv_path"]).exists())
            self.assertEqual("fail", summary["validation_gate_overall_decision"])
            self.assertEqual(0, int(summary["validation_gate_passed_modelset_count"]))
            self.assertEqual(1, int(summary["validation_gate_total_modelset_count"]))
            self.assertEqual("rule_score+logreg", summary["validation_gate_recommended_modelset_key"])
            self.assertNotEqual(summary["summary_json_path"], summary["focus_seed_compare_summary_json_path"])
            self.assertTrue(Path(summary["auto_workflow_summary_json_path"]).exists())
            self.assertTrue(Path(summary["auto_workflow_candidates_path"]).exists())

    def test_run_focus_seed_pipeline_auto_select_with_quality_gate_generates_gate_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_seed_pipeline_quality_gate_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Seed Pipeline Quality Gate Area |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_focus_seed_pipeline(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_seed_pipeline_quality_gate",
                benchmark_modelsets=[["rule_score", "logreg"]],
                seed_values=[42],
                auto_select_focus_mmsis=True,
                auto_select_count=2,
                auto_select_start_rank=1,
                auto_select_workflow_output_dir=root / "auto_focus_workflow",
                auto_candidate_quality_gate_apply=True,
                auto_candidate_quality_gate_strict=True,
                auto_candidate_quality_gate_min_row_count=1,
                auto_candidate_quality_gate_min_observed_row_count=1,
                auto_candidate_quality_gate_max_interpolation_ratio=1.0,
                auto_candidate_quality_gate_min_heading_coverage_ratio=0.0,
                auto_candidate_quality_gate_min_movement_ratio=0.0,
                auto_candidate_quality_gate_min_active_window_ratio=0.0,
                auto_candidate_quality_gate_min_average_nearby_targets=0.0,
                auto_candidate_quality_gate_max_segment_break_count=999999,
                auto_candidate_quality_gate_min_candidate_score=0.0,
                auto_candidate_quality_gate_min_recommended_target_count=0,
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
                torch_device="cpu",
            )
            self.assertEqual("completed", summary["status"])
            self.assertTrue(summary["auto_candidate_quality_gate_applied"])
            self.assertTrue(summary["auto_candidate_quality_gate_strict"])
            self.assertGreaterEqual(int(summary["auto_candidate_quality_gate_candidate_count"]), 1)
            self.assertGreaterEqual(int(summary["auto_candidate_quality_gate_passed_count"]), 1)
            self.assertFalse(summary["auto_candidate_quality_gate_fallback_used"])
            self.assertTrue(Path(summary["auto_candidate_quality_gate_summary_json_path"]).exists())
            self.assertTrue(Path(summary["auto_candidate_quality_gate_summary_md_path"]).exists())
            self.assertTrue(Path(summary["auto_candidate_quality_gate_rows_csv_path"]).exists())
            self.assertGreaterEqual(len(summary.get("focus_own_ship_mmsis", [])), 1)

    def test_focus_seed_pipeline_cli_runs_with_manual_mmsi(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_seed_pipeline_cli_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Seed Pipeline CLI Area |",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.focus_seed_pipeline_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-prefix",
                    str(root / "focus_seed_pipeline_cli"),
                    "--output-root",
                    str(root / "outputs"),
                    "--focus-own-ship-mmsis",
                    "440000102",
                    "--seed-values",
                    "42",
                    "--benchmark-modelsets",
                    "rule_score,logreg",
                    "--no-run-calibration-eval",
                    "--no-run-own-ship-loo",
                    "--run-own-ship-case-eval",
                    "--own-ship-case-eval-min-rows",
                    "5",
                    "--own-ship-case-eval-repeat-count",
                    "2",
                    "--torch-device",
                    "cpu",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            self.assertIn("validation_gate_overall_decision=", result.stdout)
            summary_json = root / "focus_seed_pipeline_cli_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual("manual", payload["focus_mmsi_resolution_mode"])
            self.assertEqual(["440000102"], payload["focus_own_ship_mmsis"])
            self.assertNotEqual(payload["summary_json_path"], payload["focus_seed_compare_summary_json_path"])
            self.assertTrue(Path(payload["focus_seed_compare_summary_json_path"]).exists())
            self.assertTrue(Path(payload["validation_gate_rows_csv_path"]).exists())

    def test_run_focus_seed_pipeline_auto_select_with_quality_gate_strict_raises_when_all_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_seed_pipeline_quality_gate_strict_fail_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Seed Pipeline Strict Fail Area |",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "quality gate rejected every own-ship candidate"):
                run_focus_seed_pipeline(
                    manifest_path=manifest,
                    raw_input_path="examples/sample_ais.csv",
                    output_prefix=root / "focus_seed_pipeline_quality_gate_strict_fail",
                    benchmark_modelsets=[["rule_score", "logreg"]],
                    seed_values=[42],
                    auto_select_focus_mmsis=True,
                    auto_select_count=2,
                    auto_select_start_rank=1,
                    auto_select_workflow_output_dir=root / "auto_focus_workflow",
                    auto_candidate_quality_gate_apply=True,
                    auto_candidate_quality_gate_strict=True,
                    auto_candidate_quality_gate_min_row_count=999999,
                    output_root=root / "outputs",
                    run_calibration_eval=False,
                    run_own_ship_loo=False,
                    run_own_ship_case_eval=True,
                    own_ship_case_eval_min_rows=5,
                    own_ship_case_eval_repeat_count=2,
                    torch_device="cpu",
                )


if __name__ == "__main__":
    unittest.main()
