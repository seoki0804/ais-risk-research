from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.noaa_focus_pairwise_bundle import run_noaa_focus_pairwise_bundle


class NoaaFocusPairwiseBundleTest(unittest.TestCase):
    def test_run_noaa_focus_pairwise_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_input = Path("/Users/seoki/Desktop/research/examples/sample_ais.csv")

            summary = run_noaa_focus_pairwise_bundle(
                raw_input_path=raw_input,
                output_prefix=root / "bundle",
                region_specs=[
                    {
                        "label": "sample_area",
                        "min_lat": 34.9,
                        "max_lat": 35.2,
                        "min_lon": 128.9,
                        "max_lon": 129.2,
                        "own_mmsis": ["440000001", "440000102"],
                    }
                ],
                source_preset="noaa_accessais",
                start_time="2026-03-07T08:58:00Z",
                end_time="2026-03-07T09:10:00Z",
                pairwise_sample_every=1,
                pairwise_max_timestamps_per_ship=50,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, summary["run_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            run = summary["runs"][0]
            self.assertGreater(run["focus_output_rows"], 0)
            self.assertGreater(run["trajectory_output_rows"], 0)
            self.assertGreater(run["pairwise_row_count"], 0)
            self.assertTrue(Path(run["focus_csv_path"]).exists())
            self.assertTrue(Path(run["tracks_csv_path"]).exists())
            self.assertTrue(Path(run["pairwise_csv_path"]).exists())

    def test_noaa_focus_pairwise_bundle_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_input = Path("/Users/seoki/Desktop/research/examples/sample_ais.csv")
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.noaa_focus_pairwise_bundle_cli",
                    "--raw-input",
                    str(raw_input),
                    "--output-prefix",
                    str(root / "bundle_cli"),
                    "--region",
                    "sample_area|34.9|35.2|128.9|129.2|440000001,440000102",
                    "--source-preset",
                    "noaa_accessais",
                    "--start-time",
                    "2026-03-07T08:58:00Z",
                    "--end-time",
                    "2026-03-07T09:10:00Z",
                    "--pairwise-sample-every",
                    "1",
                    "--pairwise-max-timestamps-per-ship",
                    "50",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            summary_json = root / "bundle_cli_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual("completed", payload["status"])
            self.assertEqual(1, payload["run_count"])
            self.assertGreater(payload["runs"][0]["pairwise_row_count"], 0)


if __name__ == "__main__":
    unittest.main()

