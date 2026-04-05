from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import preprocess_ais_csv
from ais_risk.scenario_shift_eval import run_scenario_shift_multi_snapshot
from ais_risk.scenario_threshold_sweep import run_scenario_threshold_sweep


def _write_pairwise_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["timestamp", "own_mmsi", "local_target_count", "rule_score"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            [
                {"timestamp": "2026-03-07T09:00:00Z", "own_mmsi": "440000001", "local_target_count": "4", "rule_score": "0.61"},
                {"timestamp": "2026-03-07T09:02:00Z", "own_mmsi": "440000001", "local_target_count": "3", "rule_score": "0.52"},
                {"timestamp": "2026-03-07T09:00:00Z", "own_mmsi": "440000102", "local_target_count": "2", "rule_score": "0.63"},
                {"timestamp": "2026-03-07T09:02:00Z", "own_mmsi": "440000102", "local_target_count": "2", "rule_score": "0.58"},
            ]
        )


class ScenarioThresholdSweepTest(unittest.TestCase):
    def test_run_scenario_threshold_sweep_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            curated = root / "sample_curated.csv"
            preprocess_ais_csv("examples/sample_ais.csv", curated)
            pairwise = root / "pairwise.csv"
            _write_pairwise_csv(pairwise)

            scenario_shift_summary = run_scenario_shift_multi_snapshot(
                run_specs=[
                    {
                        "label": "sample_area",
                        "pairwise_path": str(pairwise),
                        "curated_path": str(curated),
                    }
                ],
                output_prefix=root / "scenario_shift_multi",
                sample_count=2,
                min_pair_rows=1,
                min_local_target_count=1.0,
                min_snapshot_targets=1,
                min_time_gap_minutes=0.0,
            )

            summary = run_scenario_threshold_sweep(
                scenario_shift_summary_path=scenario_shift_summary["summary_json_path"],
                output_prefix=root / "threshold_sweep",
                threshold_profiles=[
                    {"name": "base", "safe": 0.35, "warning": 0.65},
                    {"name": "sensitive", "safe": 0.30, "warning": 0.60},
                ],
                baseline_profile="base",
                save_profile_results=False,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["profile_count"])
            self.assertEqual(2, summary["sample_count"])
            self.assertEqual(4, summary["row_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["rows_csv_path"]).exists())
            first_run = summary["runs"][0]
            self.assertEqual("sample_area", first_run["label"])
            self.assertEqual(2, len(first_run["profiles"]))

    def test_scenario_threshold_sweep_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            curated = root / "sample_curated.csv"
            preprocess_ais_csv("examples/sample_ais.csv", curated)
            pairwise = root / "pairwise.csv"
            _write_pairwise_csv(pairwise)
            scenario_shift_summary = run_scenario_shift_multi_snapshot(
                run_specs=[
                    {
                        "label": "sample_area",
                        "pairwise_path": str(pairwise),
                        "curated_path": str(curated),
                    }
                ],
                output_prefix=root / "scenario_shift_multi",
                sample_count=2,
                min_pair_rows=1,
                min_local_target_count=1.0,
                min_snapshot_targets=1,
                min_time_gap_minutes=0.0,
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.scenario_threshold_sweep_cli",
                    "--scenario-shift-summary",
                    str(scenario_shift_summary["summary_json_path"]),
                    "--output-prefix",
                    str(root / "threshold_sweep_cli"),
                    "--profile",
                    "base:0.35:0.65",
                    "--profile",
                    "sensitive:0.30:0.60",
                    "--baseline-profile",
                    "base",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            summary_json = root / "threshold_sweep_cli_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual("completed", payload["status"])
            self.assertEqual(2, payload["profile_count"])
            self.assertTrue((root / "threshold_sweep_cli_summary.md").exists())
            self.assertTrue((root / "threshold_sweep_cli_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
