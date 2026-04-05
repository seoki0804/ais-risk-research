from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.prediction_grid_projection import run_prediction_grid_projection


class PredictionGridProjectionTest(unittest.TestCase):
    def test_run_prediction_grid_projection_builds_case_summaries_and_selected_cells(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pairwise_path = root / "pairwise.csv"
            sample_bands_path = root / "sample_bands.csv"
            config_path = root / "config.toml"
            output_prefix = root / "projection"

            config_path.write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "Projection Test"',
                        "",
                        "[grid]",
                        "radius_nm = 0.20",
                        "cell_size_m = 100.0",
                        "kernel_sigma_m = 100.0",
                        "",
                        "[horizon]",
                        "minutes = 15",
                        "time_step_seconds = 30",
                        "",
                        "[thresholds]",
                        "safe = 0.35",
                        "warning = 0.65",
                        "density_radius_nm = 2.0",
                        "density_reference_count = 6.0",
                        "",
                        "[weights]",
                        "distance = 0.15",
                        "dcpa = 0.20",
                        "tcpa = 0.20",
                        "bearing = 0.10",
                        "relspeed = 0.10",
                        "encounter = 0.15",
                        "density = 0.10",
                        "",
                        "[scenarios]",
                        'order = ["current"]',
                        "",
                        "[scenarios.values]",
                        "current = 1.0",
                    ]
                ),
                encoding="utf-8",
            )

            with pairwise_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "timestamp",
                        "own_mmsi",
                        "target_mmsi",
                        "distance_nm",
                        "relative_bearing_deg",
                        "encounter_type",
                        "target_vessel_type",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000101",
                            "distance_nm": "0.05",
                            "relative_bearing_deg": "90",
                            "encounter_type": "crossing",
                            "target_vessel_type": "cargo",
                        },
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000102",
                            "distance_nm": "0.05",
                            "relative_bearing_deg": "0",
                            "encounter_type": "head_on",
                            "target_vessel_type": "tanker",
                        },
                    ]
                )

            with sample_bands_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "timestamp",
                        "own_mmsi",
                        "target_mmsi",
                        "label_future_conflict",
                        "model",
                        "score_lower",
                        "score_mean",
                        "score_upper",
                        "band_width",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000101",
                            "label_future_conflict": "1",
                            "model": "hgbt",
                            "score_lower": "0.20",
                            "score_mean": "0.40",
                            "score_upper": "0.60",
                            "band_width": "0.40",
                        },
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000102",
                            "label_future_conflict": "0",
                            "model": "hgbt",
                            "score_lower": "0.10",
                            "score_mean": "0.30",
                            "score_upper": "0.50",
                            "band_width": "0.40",
                        },
                        {
                            "timestamp": "2026-03-16T09:05:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000999",
                            "label_future_conflict": "0",
                            "model": "hgbt",
                            "score_lower": "0.05",
                            "score_mean": "0.07",
                            "score_upper": "0.10",
                            "band_width": "0.05",
                        },
                    ]
                )

            summary = run_prediction_grid_projection(
                pairwise_csv_path=pairwise_path,
                sample_bands_csv_path=sample_bands_path,
                output_prefix=output_prefix,
                config_path=config_path,
                case_limit=1,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, int(summary["projected_target_rows"]))
            self.assertEqual(1, int(summary["unmatched_sample_rows"]))
            self.assertEqual(1, int(summary["case_summary_rows"]))
            self.assertEqual(["2026-03-16T09-00-00Z__440000001__hgbt"], summary["selected_case_ids"])
            self.assertTrue(Path(summary["projected_targets_csv_path"]).exists())
            self.assertTrue(Path(summary["case_summary_csv_path"]).exists())
            self.assertTrue(Path(summary["projected_cells_csv_path"]).exists())

            with Path(summary["projected_targets_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
                target_rows = list(csv.DictReader(handle))
            self.assertEqual(2, len(target_rows))
            self.assertEqual("92.60", target_rows[0]["x_m"])
            self.assertEqual("0.00", target_rows[0]["y_m"])
            self.assertEqual("0.00", target_rows[1]["x_m"])
            self.assertEqual("92.60", target_rows[1]["y_m"])

            with Path(summary["case_summary_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
                case_rows = list(csv.DictReader(handle))
            self.assertEqual(1, len(case_rows))
            self.assertEqual("2", case_rows[0]["target_count"])
            self.assertGreater(float(case_rows[0]["max_risk_mean"]), 0.0)

            with Path(summary["projected_cells_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
                cell_rows = list(csv.DictReader(handle))
            self.assertGreater(len(cell_rows), 0)
            self.assertTrue(any(float(row["risk_mean"]) > 0.0 for row in cell_rows))


if __name__ == "__main__":
    unittest.main()
