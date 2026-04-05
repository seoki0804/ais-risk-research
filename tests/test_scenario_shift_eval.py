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


def _write_pairwise_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["timestamp", "own_mmsi", "local_target_count", "rule_score"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            [
                {"timestamp": "2026-03-07T09:00:00Z", "own_mmsi": "440000001", "local_target_count": "4", "rule_score": "0.61"},
                {"timestamp": "2026-03-07T09:00:00Z", "own_mmsi": "440000001", "local_target_count": "3", "rule_score": "0.57"},
                {"timestamp": "2026-03-07T09:02:00Z", "own_mmsi": "440000001", "local_target_count": "3", "rule_score": "0.52"},
                {"timestamp": "2026-03-07T09:02:00Z", "own_mmsi": "440000001", "local_target_count": "2", "rule_score": "0.49"},
                {"timestamp": "2026-03-07T09:00:00Z", "own_mmsi": "440000102", "local_target_count": "2", "rule_score": "0.63"},
                {"timestamp": "2026-03-07T09:00:00Z", "own_mmsi": "440000102", "local_target_count": "2", "rule_score": "0.58"},
            ]
        )


class ScenarioShiftEvalTest(unittest.TestCase):
    def test_run_scenario_shift_multi_snapshot_generates_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            curated = root / "sample_curated.csv"
            preprocess_ais_csv("examples/sample_ais.csv", curated)

            pairwise = root / "pairwise.csv"
            _write_pairwise_csv(pairwise)

            summary = run_scenario_shift_multi_snapshot(
                run_specs=[
                    {
                        "label": "sample_area",
                        "pairwise_path": str(pairwise),
                        "curated_path": str(curated),
                    }
                ],
                output_prefix=root / "scenario_shift_eval",
                sample_count=2,
                min_pair_rows=1,
                min_local_target_count=1.0,
                min_snapshot_targets=1,
                min_time_gap_minutes=0.0,
                radius_nm=6.0,
                max_age_minutes=5.0,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, summary["run_count"])
            self.assertEqual(2, summary["requested_sample_count"])
            self.assertEqual(2, summary["completed_sample_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())

            run = summary["runs"][0]
            self.assertEqual("sample_area", run["label"])
            self.assertEqual(2, run["completed_sample_count"])
            self.assertIn("speedup_mean_risk_delta", run["delta_stats_vs_current"])

    def test_scenario_shift_eval_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            curated = root / "sample_curated.csv"
            preprocess_ais_csv("examples/sample_ais.csv", curated)
            pairwise = root / "pairwise.csv"
            _write_pairwise_csv(pairwise)

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.scenario_shift_eval_cli",
                    "--run",
                    f"sample_area|{pairwise}|{curated}",
                    "--output-prefix",
                    str(root / "scenario_shift_cli"),
                    "--sample-count",
                    "2",
                    "--min-pair-rows",
                    "1",
                    "--min-local-target-count",
                    "1.0",
                    "--min-snapshot-targets",
                    "1",
                    "--min-time-gap-min",
                    "0",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            summary_json = root / "scenario_shift_cli_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual("completed", payload["status"])
            self.assertEqual(2, payload["completed_sample_count"])
            self.assertTrue((root / "scenario_shift_cli_summary.md").exists())


if __name__ == "__main__":
    unittest.main()
