from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.summary import build_markdown_summary, save_markdown_summary


class SummaryTest(unittest.TestCase):
    def test_summary_markdown_is_generated_from_aggregate_files(self) -> None:
        experiment_payload = {
            "case_count": 2,
            "own_mmsi": "440000001",
            "radius_nm": 6.0,
            "scenario_averages": {
                "slowdown": {
                    "avg_max_risk": 0.68,
                    "avg_mean_risk": 0.01,
                    "avg_warning_area_nm2": 0.05,
                    "avg_delta_max_risk_vs_current": -0.02,
                    "avg_delta_warning_area_vs_current": 0.01,
                },
                "current": {
                    "avg_max_risk": 0.70,
                    "avg_mean_risk": 0.02,
                    "avg_warning_area_nm2": 0.04,
                    "avg_delta_max_risk_vs_current": 0.0,
                    "avg_delta_warning_area_vs_current": 0.0,
                },
                "speedup": {
                    "avg_max_risk": 0.72,
                    "avg_mean_risk": 0.02,
                    "avg_warning_area_nm2": 0.03,
                    "avg_delta_max_risk_vs_current": 0.02,
                    "avg_delta_warning_area_vs_current": -0.01,
                },
            },
        }
        ablation_payload = {
            "case_count": 2,
            "own_mmsi": "440000001",
            "radius_nm": 6.0,
            "ablations": {
                "baseline": {
                    "current": {
                        "avg_max_risk": 0.70,
                        "avg_mean_risk": 0.02,
                        "avg_warning_area_nm2": 0.04,
                        "avg_delta_max_risk_vs_baseline": 0.0,
                        "avg_delta_warning_area_vs_baseline": 0.0,
                    }
                },
                "drop_bearing": {
                    "current": {
                        "avg_max_risk": 0.66,
                        "avg_mean_risk": 0.02,
                        "avg_warning_area_nm2": 0.02,
                        "avg_delta_max_risk_vs_baseline": -0.04,
                        "avg_delta_warning_area_vs_baseline": -0.02,
                    }
                },
                "drop_time_decay": {
                    "current": {
                        "avg_max_risk": 0.74,
                        "avg_mean_risk": 0.03,
                        "avg_warning_area_nm2": 0.10,
                        "avg_delta_max_risk_vs_baseline": 0.04,
                        "avg_delta_warning_area_vs_baseline": 0.06,
                    }
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            experiment_json = temp_dir_path / "experiment.json"
            ablation_json = temp_dir_path / "ablation.json"
            output_path = temp_dir_path / "summary.md"
            experiment_json.write_text(json.dumps(experiment_payload), encoding="utf-8")
            ablation_json.write_text(json.dumps(ablation_payload), encoding="utf-8")

            markdown_text = build_markdown_summary(experiment_json, ablation_json)

            self.assertIn("# Baseline Experiment Findings", markdown_text)
            self.assertIn("## Scenario Summary", markdown_text)
            self.assertIn("## Ablation Summary", markdown_text)
            self.assertIn("drop_time_decay", markdown_text)

            save_markdown_summary(output_path, markdown_text)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
