from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.study_sweep import parse_benchmark_modelsets, run_study_modelset_sweep


class StudySweepTest(unittest.TestCase):
    def test_parse_benchmark_modelsets(self) -> None:
        modelsets = parse_benchmark_modelsets("rule_score,logreg,hgbt; rule_score,logreg,hgbt,torch_mlp")
        self.assertEqual([["rule_score", "logreg", "hgbt"], ["rule_score", "logreg", "hgbt", "torch_mlp"]], modelsets)

    def test_run_study_modelset_sweep_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_sweep_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Sweep Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            summary = run_study_modelset_sweep(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "study_sweep",
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=False,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, summary["modelset_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_csv_path"]).exists())
            self.assertEqual("completed", summary["rows"][0]["status"])
            self.assertIn(summary["rows"][0]["best_benchmark_model"], {"rule_score", "logreg"})
            self.assertIn("benchmark_elapsed_seconds", summary["rows"][0])

    def test_run_study_modelset_sweep_can_build_study_journals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_sweep_journal_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Sweep Journal Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            summary = run_study_modelset_sweep(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "study_sweep_journal",
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=False,
                build_study_journals=True,
                study_journal_output_template=str(root / "journals" / "{date}_{dataset_id}_{modelset_index}.md"),
                study_journal_note="sweep journal test",
            )
            self.assertEqual("completed", summary["status"])
            row = summary["rows"][0]
            self.assertEqual("completed", row["status"])
            self.assertTrue(row.get("study_journal_path"))
            self.assertIsNone(row.get("study_journal_error"))
            journal_path = Path(str(row["study_journal_path"]))
            self.assertTrue(journal_path.exists())
            journal_text = journal_path.read_text(encoding="utf-8")
            self.assertIn("sweep journal test", journal_text)

    def test_run_study_modelset_sweep_supports_own_ship_case_mmsi_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_sweep_case_mmsi_filter_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Sweep MMSI Filter Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            summary = run_study_modelset_sweep(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "study_sweep_case_mmsi_filter",
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_mmsis=["440000102"],
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(["440000102"], summary.get("own_ship_case_eval_mmsis"))

            row = summary["rows"][0]
            self.assertEqual("completed", row["status"])
            study_summary = json.loads(Path(str(row["study_summary_json_path"])).read_text(encoding="utf-8"))
            own_ship_case_summary_path = Path(str(study_summary["own_ship_case_eval_summary_json_path"]))
            self.assertTrue(own_ship_case_summary_path.exists())
            own_ship_case_summary = json.loads(own_ship_case_summary_path.read_text(encoding="utf-8"))
            for metrics in own_ship_case_summary.get("aggregate_models", {}).values():
                self.assertEqual(1, int(metrics.get("ship_count", 0)))

    def test_study_sweep_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_sweep_cli_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Sweep CLI Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.study_sweep_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-prefix",
                    str(root / "study_sweep_cli"),
                    "--output-root",
                    str(root / "outputs"),
                    "--benchmark-modelsets",
                    "rule_score,logreg",
                    "--no-run-calibration-eval",
                    "--no-run-own-ship-loo",
                    "--no-run-own-ship-case-eval",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            self.assertTrue((root / "study_sweep_cli_summary.json").exists())
            self.assertTrue((root / "study_sweep_cli_summary.md").exists())
            self.assertTrue((root / "study_sweep_cli_rows.csv").exists())
            csv_header = (root / "study_sweep_cli_rows.csv").read_text(encoding="utf-8").splitlines()[0]
            self.assertIn("benchmark_elapsed_seconds", csv_header)

    def test_study_sweep_cli_can_build_study_journals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_sweep_cli_journal_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Sweep CLI Journal Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            journal_template = root / "journals" / "{date}_{dataset_id}_{modelset_index}.md"
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.study_sweep_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-prefix",
                    str(root / "study_sweep_cli_journal"),
                    "--output-root",
                    str(root / "outputs"),
                    "--benchmark-modelsets",
                    "rule_score,logreg",
                    "--no-run-calibration-eval",
                    "--no-run-own-ship-loo",
                    "--no-run-own-ship-case-eval",
                    "--build-study-journals",
                    "--study-journal-output-template",
                    str(journal_template),
                    "--study-journal-note",
                    "cli sweep journal test",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            summary_json = root / "study_sweep_cli_journal_summary.json"
            self.assertTrue(summary_json.exists())
            import json

            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            row = payload["rows"][0]
            self.assertTrue(row.get("study_journal_path"))
            journal_path = Path(str(row["study_journal_path"]))
            self.assertTrue(journal_path.exists())


if __name__ == "__main__":
    unittest.main()
