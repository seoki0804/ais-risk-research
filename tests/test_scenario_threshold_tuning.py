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
from ais_risk.scenario_threshold_tuning import run_scenario_threshold_tuning


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


class ScenarioThresholdTuningTest(unittest.TestCase):
    def test_run_scenario_threshold_tuning_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            curated = root / "sample_curated.csv"
            preprocess_ais_csv("examples/sample_ais.csv", curated)
            pairwise = root / "pairwise.csv"
            _write_pairwise_csv(pairwise)
            scenario_shift = run_scenario_shift_multi_snapshot(
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

            summary = run_scenario_threshold_tuning(
                scenario_shift_summary_path=scenario_shift["summary_json_path"],
                output_prefix=root / "threshold_tuning",
                safe_min=0.30,
                safe_max=0.40,
                safe_step=0.10,
                warning_min=0.60,
                warning_max=0.70,
                warning_step=0.10,
                top_k=3,
            )
            self.assertEqual("completed", summary["status"])
            self.assertGreaterEqual(summary["candidate_profile_count"], 1)
            self.assertTrue(summary.get("recommended_profile_name"))
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["rows_csv_path"]).exists())
            self.assertTrue(Path(summary["sweep_summary_path"]).exists())

    def test_scenario_threshold_tuning_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            curated = root / "sample_curated.csv"
            preprocess_ais_csv("examples/sample_ais.csv", curated)
            pairwise = root / "pairwise.csv"
            _write_pairwise_csv(pairwise)
            scenario_shift = run_scenario_shift_multi_snapshot(
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
                    "ais_risk.scenario_threshold_tuning_cli",
                    "--scenario-shift-summary",
                    str(scenario_shift["summary_json_path"]),
                    "--output-prefix",
                    str(root / "threshold_tuning_cli"),
                    "--safe-min",
                    "0.30",
                    "--safe-max",
                    "0.40",
                    "--safe-step",
                    "0.10",
                    "--warning-min",
                    "0.60",
                    "--warning-max",
                    "0.70",
                    "--warning-step",
                    "0.10",
                    "--top-k",
                    "3",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            summary_json = root / "threshold_tuning_cli_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual("completed", payload["status"])
            self.assertTrue(payload.get("recommended_profile_name"))


if __name__ == "__main__":
    unittest.main()
