from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.scenario_threshold_stability import build_scenario_threshold_stability_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class ScenarioThresholdStabilityTest(unittest.TestCase):
    def test_build_scenario_threshold_stability_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            summary_a = root / "threshold_a_summary.json"
            summary_b = root / "threshold_b_summary.json"

            _write_json(
                summary_a,
                {
                    "recommended_profile_name": "s0p35_w0p60",
                    "recommended_safe_threshold": 0.35,
                    "recommended_warning_threshold": 0.60,
                    "recommended_objective_score": 0.12,
                    "recommended_bootstrap_top1_frequency": 0.41,
                    "bootstrap_consensus_profile_name": "s0p35_w0p60",
                    "bootstrap_consensus_profile_frequency": 0.41,
                    "scenario_shift_summary_path": "outputs/day_a/scenario_shift_summary.json",
                    "top_rows": [
                        {"rank": 1, "profile_name": "s0p35_w0p60"},
                        {"rank": 2, "profile_name": "s0p35_w0p65"},
                    ],
                    "rows": [
                        {
                            "rank": 1,
                            "profile_name": "s0p35_w0p60",
                            "objective_score": 0.12,
                            "bootstrap_top1_frequency": 0.41,
                            "safe_threshold": 0.35,
                            "warning_threshold": 0.60,
                        },
                        {
                            "rank": 2,
                            "profile_name": "s0p35_w0p65",
                            "objective_score": 0.16,
                            "bootstrap_top1_frequency": 0.32,
                            "safe_threshold": 0.35,
                            "warning_threshold": 0.65,
                        },
                    ],
                },
            )
            _write_json(
                summary_b,
                {
                    "recommended_profile_name": "s0p35_w0p60",
                    "recommended_safe_threshold": 0.35,
                    "recommended_warning_threshold": 0.60,
                    "recommended_objective_score": 0.10,
                    "recommended_bootstrap_top1_frequency": 0.37,
                    "bootstrap_consensus_profile_name": "s0p35_w0p60",
                    "bootstrap_consensus_profile_frequency": 0.37,
                    "scenario_shift_summary_path": "outputs/day_b/scenario_shift_summary.json",
                    "top_rows": [
                        {"rank": 1, "profile_name": "s0p35_w0p60"},
                        {"rank": 2, "profile_name": "s0p35_w0p65"},
                    ],
                    "rows": [
                        {
                            "rank": 1,
                            "profile_name": "s0p35_w0p60",
                            "objective_score": 0.10,
                            "bootstrap_top1_frequency": 0.37,
                            "safe_threshold": 0.35,
                            "warning_threshold": 0.60,
                        },
                        {
                            "rank": 2,
                            "profile_name": "s0p35_w0p65",
                            "objective_score": 0.15,
                            "bootstrap_top1_frequency": 0.30,
                            "safe_threshold": 0.35,
                            "warning_threshold": 0.65,
                        },
                    ],
                },
            )

            summary = build_scenario_threshold_stability_report(
                summary_specs=[
                    {"label": "day_a", "summary_path": str(summary_a)},
                    {"label": "day_b", "summary_path": str(summary_b)},
                ],
                output_prefix=root / "threshold_stability",
                top_k=2,
                shortlist_size=2,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["source_count"])
            self.assertEqual("stable", summary["stability_status"])
            self.assertEqual("s0p35_w0p60", summary["recommendation_majority_profile"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["run_rows_csv_path"]).exists())
            self.assertTrue(Path(summary["profile_rows_csv_path"]).exists())
            self.assertEqual("s0p35_w0p60", summary["shortlist"][0]["profile_name"])

    def test_scenario_threshold_stability_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            summary_a = root / "a_summary.json"
            summary_b = root / "b_summary.json"
            _write_json(
                summary_a,
                {
                    "recommended_profile_name": "s0p35_w0p60",
                    "recommended_bootstrap_top1_frequency": 0.20,
                    "bootstrap_consensus_profile_name": "s0p35_w0p60",
                    "bootstrap_consensus_profile_frequency": 0.20,
                    "top_rows": [
                        {"rank": 1, "profile_name": "s0p35_w0p60"},
                        {"rank": 2, "profile_name": "s0p35_w0p65"},
                    ],
                    "rows": [
                        {
                            "rank": 1,
                            "profile_name": "s0p35_w0p60",
                            "objective_score": 0.10,
                            "bootstrap_top1_frequency": 0.20,
                            "safe_threshold": 0.35,
                            "warning_threshold": 0.60,
                        }
                    ],
                },
            )
            _write_json(
                summary_b,
                {
                    "recommended_profile_name": "s0p35_w0p65",
                    "recommended_bootstrap_top1_frequency": 0.20,
                    "bootstrap_consensus_profile_name": "s0p35_w0p65",
                    "bootstrap_consensus_profile_frequency": 0.20,
                    "top_rows": [
                        {"rank": 1, "profile_name": "s0p35_w0p65"},
                        {"rank": 2, "profile_name": "s0p35_w0p60"},
                    ],
                    "rows": [
                        {
                            "rank": 1,
                            "profile_name": "s0p35_w0p65",
                            "objective_score": 0.09,
                            "bootstrap_top1_frequency": 0.20,
                            "safe_threshold": 0.35,
                            "warning_threshold": 0.65,
                        }
                    ],
                },
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.scenario_threshold_stability_cli",
                    "--summary-json",
                    str(summary_a),
                    "--summary-json",
                    str(summary_b),
                    "--output-prefix",
                    str(root / "threshold_stability_cli"),
                    "--top-k",
                    "2",
                    "--shortlist-size",
                    "2",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            summary_json = root / "threshold_stability_cli_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual("completed", payload["status"])
            self.assertEqual(2, payload["source_count"])
            self.assertEqual("unstable", payload["stability_status"])


if __name__ == "__main__":
    unittest.main()

