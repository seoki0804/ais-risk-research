from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import os
import subprocess
import json

from ais_risk.study_run import run_dataset_study_from_manifest


class StudyRunTest(unittest.TestCase):
    def test_run_dataset_study_from_manifest_creates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_study_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_dataset_study_from_manifest(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_root=root / "outputs",
                run_error_analysis=True,
                run_stratified_eval=True,
                run_calibration_eval=True,
                run_own_ship_loo=True,
                run_own_ship_case_eval=True,
                run_validation_suite_flag=True,
                update_validation_leaderboard=True,
                validation_leaderboard_study_glob=str(root / "outputs" / "*_study_summary.json"),
                validation_leaderboard_csv_path=root / "outputs" / "leaderboard.csv",
                validation_leaderboard_md_path=root / "outputs" / "leaderboard.md",
                run_mps_benchmark=False,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual("sample_study_case_v1", summary["dataset_id"])
            self.assertEqual("2026-03-07", summary["start_date"])
            self.assertEqual("2026-03-08", summary["end_date"])
            self.assertEqual("timestamp", summary["pairwise_split_strategy"])
            self.assertTrue(summary["error_analysis_enabled"])
            self.assertTrue(summary["stratified_eval_enabled"])
            self.assertTrue(summary["calibration_eval_enabled"])
            self.assertTrue(summary["own_ship_loo_enabled"])
            self.assertTrue(summary["own_ship_case_eval_enabled"])
            self.assertTrue(summary["validation_suite_enabled"])
            self.assertTrue(summary["validation_leaderboard_updated"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["workflow"]["summary_json_path"]).exists())
            self.assertTrue(Path(summary["pairwise"]["dataset_path"]).exists())
            self.assertTrue(Path(summary["benchmark"]["summary_json_path"]).exists())
            self.assertTrue(Path(summary["research_log_path"]).exists())
            self.assertTrue(Path(summary["error_analysis_summary_json_path"]).exists())
            self.assertTrue(Path(summary["stratified_eval_summary_json_path"]).exists())
            self.assertTrue(Path(summary["calibration_eval_summary_json_path"]).exists())
            self.assertTrue(Path(summary["own_ship_loo_summary_json_path"]).exists())
            self.assertTrue(Path(summary["own_ship_case_eval_summary_json_path"]).exists())
            self.assertTrue(Path(summary["own_ship_case_eval_repeat_metrics_csv_path"]).exists())
            self.assertTrue(Path(summary["validation_suite_summary_json_path"]).exists())
            self.assertTrue(Path(summary["validation_leaderboard_csv_path"]).exists())

    def test_run_dataset_study_auto_merges_raw_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_study_case_v2`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Area 2 |",
                    ]
                ),
                encoding="utf-8",
            )
            downloads = root / "downloads"
            downloads.mkdir(parents=True, exist_ok=True)
            (downloads / "day1.csv").write_text(
                "MMSI,BaseDateTime,LAT,LON,SOG,COG,Heading,VesselType\n"
                "440000001,2026-03-07T09:00:00Z,35.050000,129.050000,12.0,45.0,45.0,cargo\n"
                "440000101,2026-03-07T09:00:00Z,35.072000,129.078000,12.5,225.0,225.0,cargo\n",
                encoding="utf-8",
            )
            (downloads / "day2.csv").write_text(
                "MMSI,BaseDateTime,LAT,LON,SOG,COG,Heading,VesselType\n"
                "440000001,2026-03-07T09:02:00Z,35.051000,129.051000,12.0,45.0,45.0,cargo\n"
                "440000101,2026-03-07T09:02:00Z,35.070000,129.076000,12.5,225.0,225.0,cargo\n",
                encoding="utf-8",
            )

            raw_input = root / "raw.csv"
            summary = run_dataset_study_from_manifest(
                manifest_path=manifest,
                raw_input_path=raw_input,
                output_root=root / "outputs",
                auto_merge_input_glob=str(downloads / "*.csv"),
                run_mps_benchmark=False,
            )

            self.assertTrue(raw_input.exists())
            self.assertIn("raw_merge", summary)
            self.assertGreater(summary["raw_merge"]["output_rows"], 0)
            self.assertTrue(Path(summary["summary_json_path"]).exists())

    def test_study_run_cli_can_build_study_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_study_cli_journal_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Study CLI Journal |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            journal_path = root / "study_journal.md"
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.study_run_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-root",
                    str(root / "outputs"),
                    "--run-calibration-eval",
                    "--run-own-ship-case-eval",
                    "--build-study-journal",
                    "--study-journal-output",
                    str(journal_path),
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("study_journal=", result.stdout)
            self.assertTrue(journal_path.exists())

    def test_study_run_cli_supports_noaa_fetch_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_study_noaa_fetch_cli_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample NOAA Fetch CLI |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )
            fetch_summary_path = root / "fetch_summary.json"
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.study_run_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-root",
                    str(root / "outputs"),
                    "--fetch-noaa",
                    "--fetch-dry-run",
                    "--fetch-summary-json",
                    str(fetch_summary_path),
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("fetch_provider=noaa", result.stdout)
            self.assertIn("fetch_status=dry_run", result.stdout)
            self.assertTrue(fetch_summary_path.exists())
            payload = json.loads(fetch_summary_path.read_text(encoding="utf-8"))
            self.assertEqual("dry_run", payload.get("status"))
            self.assertEqual(2, payload.get("planned_count"))

    def test_run_dataset_study_supports_custom_benchmark_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_study_models_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Models Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_dataset_study_from_manifest(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_root=root / "outputs",
                benchmark_models=["rule_score", "logreg"],
                run_mps_benchmark=False,
            )
            self.assertEqual(["rule_score", "logreg"], summary["benchmark_models"])
            benchmark_summary = json.loads(Path(summary["benchmark"]["summary_json_path"]).read_text(encoding="utf-8"))
            self.assertEqual({"rule_score", "logreg"}, set(benchmark_summary.get("models", {}).keys()))

    def test_run_dataset_study_supports_source_preset_passthrough(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_study_noaa_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample NOAA Area |",
                        "| 시작 시각 | 2026-03-07 |",
                        "| 종료 시각 | 2026-03-08 |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_dataset_study_from_manifest(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_root=root / "outputs",
                source_preset_name="noaa_accessais",
                benchmark_models=["rule_score", "logreg"],
                run_mps_benchmark=False,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual("noaa_accessais", summary["ingestion_source_preset"])
            self.assertEqual(
                "noaa_accessais",
                summary.get("workflow", {}).get("resolved_ingestion", {}).get("source_preset"),
            )


if __name__ == "__main__":
    unittest.main()
