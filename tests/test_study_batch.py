from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import json

from ais_risk.study_batch import run_study_batch_from_manifest_glob


class StudyBatchTest(unittest.TestCase):
    def test_run_study_batch_from_manifest_glob_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_dir = root / "manifests"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_a = manifest_dir / "a.md"
            manifest_b = manifest_dir / "b.md"
            manifest_a.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_batch_case_a_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Batch A |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            manifest_b.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_batch_case_b_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Batch B |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_study_batch_from_manifest_glob(
                manifest_glob=str(manifest_dir / "*.md"),
                output_prefix=root / "batch_run",
                raw_input_template="examples/sample_ais.csv",
                output_root=root / "outputs",
                continue_on_error=True,
                run_calibration_eval=True,
                run_own_ship_case_eval=True,
                run_mps_benchmark=False,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["total_manifests"])
            self.assertEqual(2, summary["completed_count"])
            self.assertEqual(0, summary["failed_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            first_item = summary["items"][0]
            self.assertTrue(Path(first_item["calibration_eval_summary_json_path"]).exists())
            self.assertTrue(Path(first_item["own_ship_case_eval_summary_json_path"]).exists())
            self.assertTrue(Path(first_item["own_ship_case_eval_repeat_metrics_csv_path"]).exists())

    def test_run_study_batch_can_continue_on_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_dir = root / "manifests"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_a = manifest_dir / "a.md"
            manifest_b = manifest_dir / "b.md"
            manifest_a.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_batch_fail_a_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Batch Fail A |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            manifest_b.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_batch_fail_b_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Batch Fail B |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_study_batch_from_manifest_glob(
                manifest_glob=str(manifest_dir / "*.md"),
                output_prefix=root / "batch_run_fail",
                raw_input_template="data/raw/{source_slug}/{dataset_id}/raw.csv",
                output_root=root / "outputs",
                continue_on_error=True,
                run_mps_benchmark=False,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["total_manifests"])
            self.assertEqual(0, summary["completed_count"])
            self.assertEqual(2, summary["failed_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())

    def test_study_batch_cli_can_build_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_dir = root / "manifests"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest = manifest_dir / "a.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_batch_cli_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Batch CLI |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            review_path = root / "batch_review.md"
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.study_batch_cli",
                    "--manifest-glob",
                    str(manifest_dir / "*.md"),
                    "--output-prefix",
                    str(root / "batch_run"),
                    "--raw-input-template",
                    "examples/sample_ais.csv",
                    "--max-manifests",
                    "1",
                    "--build-batch-review",
                    "--batch-review-output",
                    str(review_path),
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("batch_review=", result.stdout)
            self.assertTrue(review_path.exists())

    def test_study_batch_cli_can_build_trend_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_dir = root / "manifests"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest = manifest_dir / "a.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_batch_cli_trend_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Batch CLI Trend |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            trend_prefix = root / "batch_trend"
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.study_batch_cli",
                    "--manifest-glob",
                    str(manifest_dir / "*.md"),
                    "--output-prefix",
                    str(root / "study_batch_run"),
                    "--raw-input-template",
                    "examples/sample_ais.csv",
                    "--max-manifests",
                    "1",
                    "--run-calibration-eval",
                    "--run-own-ship-case-eval",
                    "--own-ship-case-eval-min-rows",
                    "5",
                    "--build-batch-trend-report",
                    "--batch-trend-output-prefix",
                    str(trend_prefix),
                    "--batch-trend-history-glob",
                    str(root / "*study_batch*_summary.json"),
                    "--batch-trend-moving-average-window",
                    "2",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("batch_trend_summary_json=", result.stdout)
            self.assertTrue((root / "batch_trend_summary.json").exists())
            self.assertTrue((root / "batch_trend_summary.md").exists())
            self.assertTrue((root / "batch_trend_dataset_trends.csv").exists())

    def test_study_batch_cli_can_build_study_journals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_dir = root / "manifests"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest = manifest_dir / "a.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_batch_cli_journal_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Batch CLI Journal |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            journal_template = str(root / "{date}_{dataset_id}_study_journal.md")
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.study_batch_cli",
                    "--manifest-glob",
                    str(manifest_dir / "*.md"),
                    "--output-prefix",
                    str(root / "study_batch_run"),
                    "--raw-input-template",
                    "examples/sample_ais.csv",
                    "--max-manifests",
                    "1",
                    "--build-study-journals",
                    "--study-journal-output-template",
                    journal_template,
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("study_journal_count=1", result.stdout)
            generated = list(root.glob("*_sample_batch_cli_journal_v1_study_journal.md"))
            self.assertEqual(1, len(generated))
            self.assertTrue(generated[0].exists())

    def test_run_study_batch_supports_custom_benchmark_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_dir = root / "manifests"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest = manifest_dir / "a.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_batch_models_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Batch Models |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_study_batch_from_manifest_glob(
                manifest_glob=str(manifest_dir / "*.md"),
                output_prefix=root / "study_batch_models",
                raw_input_template="examples/sample_ais.csv",
                output_root=root / "outputs",
                max_manifests=1,
                benchmark_models=["rule_score", "hgbt"],
                run_mps_benchmark=False,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, summary["completed_count"])
            item = summary["items"][0]
            study_summary = json.loads(Path(item["study_summary_json_path"]).read_text(encoding="utf-8"))
            self.assertEqual(["rule_score", "hgbt"], study_summary.get("benchmark_models"))


if __name__ == "__main__":
    unittest.main()
