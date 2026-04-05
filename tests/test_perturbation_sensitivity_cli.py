from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.perturbation_sensitivity_cli import main


class PerturbationSensitivityCliTest(unittest.TestCase):
    def test_cli_builds_summary_from_stubbed_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline_pairwise = root / "baseline_pairwise.csv"
            baseline_predictions = root / "baseline_test_predictions.csv"
            baseline_summary = root / "baseline_summary.json"
            config_path = root / "config.toml"
            perturbed_pairwise = root / "perturbed_pairwise.csv"
            perturbed_predictions = root / "perturbed_test_predictions.csv"
            baseline_case_summary = root / "baseline_case_summary.csv"
            perturbed_case_summary = root / "perturbed_case_summary.csv"

            config_path.write_text("[project]\nname='test'\n[grid]\nradius_nm=1.0\ncell_size_m=100.0\nkernel_sigma_m=100.0\n[horizon]\nminutes=15\ntime_step_seconds=30\n[thresholds]\nsafe=0.2\nwarning=0.4\ndensity_radius_nm=2.0\ndensity_reference_count=6.0\n[weights]\ndistance=0.15\ndcpa=0.20\ntcpa=0.20\nbearing=0.10\nrelspeed=0.10\nencounter=0.15\ndensity=0.10\n[scenarios]\norder=['current']\n[scenarios.values]\ncurrent=1.0\n", encoding="utf-8")

            with baseline_pairwise.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["timestamp", "own_mmsi", "target_mmsi", "distance_nm", "relative_bearing_deg"])
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-03-16T09:00:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": "440000101",
                        "distance_nm": "1.0",
                        "relative_bearing_deg": "30.0",
                    }
                )

            with baseline_predictions.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["timestamp", "own_mmsi", "target_mmsi", "label_future_conflict", "hgbt_score", "hgbt_pred"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-03-16T09:00:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": "440000101",
                        "label_future_conflict": "1",
                        "hgbt_score": "0.70",
                        "hgbt_pred": "1",
                    }
                )

            baseline_summary.write_text(json.dumps({"models": {"hgbt": {"f1": 0.8}}}), encoding="utf-8")

            with perturbed_pairwise.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["timestamp", "own_mmsi", "target_mmsi", "distance_nm", "relative_bearing_deg"])
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-03-16T09:00:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": "440000101",
                        "distance_nm": "1.1",
                        "relative_bearing_deg": "35.0",
                    }
                )

            with perturbed_predictions.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["timestamp", "own_mmsi", "target_mmsi", "label_future_conflict", "hgbt_score", "hgbt_pred"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-03-16T09:00:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": "440000101",
                        "label_future_conflict": "1",
                        "hgbt_score": "0.55",
                        "hgbt_pred": "1",
                    }
                )

            with baseline_case_summary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["case_id", "max_risk_mean", "warning_area_mean_nm2", "caution_area_mean_nm2"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "case_id": "2026-03-16T09-00-00Z__440000001__hgbt",
                        "max_risk_mean": "0.7",
                        "warning_area_mean_nm2": "0.4",
                        "caution_area_mean_nm2": "0.8",
                    }
                )

            with perturbed_case_summary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["case_id", "max_risk_mean", "warning_area_mean_nm2", "caution_area_mean_nm2"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "case_id": "2026-03-16T09-00-00Z__440000001__hgbt",
                        "max_risk_mean": "0.6",
                        "warning_area_mean_nm2": "0.3",
                        "caution_area_mean_nm2": "0.9",
                    }
                )

            def fake_run_pairwise_perturbation(**_: object) -> dict[str, object]:
                return {
                    "summary_json_path": str(root / "perturbation_summary.json"),
                    "perturbed_csv_path": str(perturbed_pairwise),
                }

            def fake_run_pairwise_benchmark(**_: object) -> dict[str, object]:
                return {
                    "summary_json_path": str(root / "perturbed_benchmark_summary.json"),
                    "predictions_csv_path": str(perturbed_predictions),
                    "models": {"hgbt": {"f1": 0.6}},
                }

            calibration_calls = {"count": 0}

            def fake_run_calibration_evaluation(**_: object) -> dict[str, object]:
                calibration_calls["count"] += 1
                ece = 0.05 if calibration_calls["count"] == 1 else 0.12
                return {"models": {"hgbt": {"ece": ece}}}

            projection_calls = {"count": 0}

            def fake_run_prediction_grid_projection(**_: object) -> dict[str, object]:
                projection_calls["count"] += 1
                case_summary_path = baseline_case_summary if projection_calls["count"] == 1 else perturbed_case_summary
                return {
                    "case_summary_csv_path": str(case_summary_path),
                    "summary_json_path": str(root / f"projection_{projection_calls['count']}.json"),
                }

            output_prefix = root / "sensitivity"
            argv = [
                "perturbation_sensitivity_cli",
                "--baseline-pairwise",
                str(baseline_pairwise),
                "--baseline-predictions",
                str(baseline_predictions),
                "--output-prefix",
                str(output_prefix),
                "--config",
                str(config_path),
            ]

            with patch("ais_risk.perturbation_sensitivity_cli.run_pairwise_perturbation", side_effect=fake_run_pairwise_perturbation), patch(
                "ais_risk.perturbation_sensitivity_cli.run_pairwise_benchmark", side_effect=fake_run_pairwise_benchmark
            ), patch(
                "ais_risk.perturbation_sensitivity_cli.run_calibration_evaluation", side_effect=fake_run_calibration_evaluation
            ), patch(
                "ais_risk.perturbation_sensitivity_cli.run_prediction_grid_projection",
                side_effect=fake_run_prediction_grid_projection,
            ), patch("sys.argv", argv):
                main()

            summary_path = root / "sensitivity_summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual("completed", summary["status"])
            self.assertAlmostEqual(-0.2, float(summary["delta_f1"]), places=6)
            self.assertAlmostEqual(0.07, float(summary["delta_ece"]), places=6)
            self.assertTrue(summary["top_case_preserved"])
            self.assertAlmostEqual(-0.1, float(summary["delta_case_max_risk_mean"]), places=6)


if __name__ == "__main__":
    unittest.main()
