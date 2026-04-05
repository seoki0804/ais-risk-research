from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.pairwise_perturbation import run_pairwise_perturbation


class PairwisePerturbationTest(unittest.TestCase):
    def test_run_pairwise_perturbation_recomputes_geometry_and_rule_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.toml"
            pairwise_path = root / "pairwise.csv"
            output_prefix = root / "perturb"

            config_path.write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "Perturb Test"',
                        "",
                        "[grid]",
                        "radius_nm = 6.0",
                        "cell_size_m = 250.0",
                        "kernel_sigma_m = 200.0",
                        "",
                        "[horizon]",
                        "minutes = 15",
                        "time_step_seconds = 30",
                        "",
                        "[thresholds]",
                        "safe = 0.25",
                        "warning = 0.55",
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
                        "own_segment_id",
                        "target_segment_id",
                        "own_vessel_type",
                        "target_vessel_type",
                        "own_is_interpolated",
                        "target_is_interpolated",
                        "local_target_count",
                        "distance_nm",
                        "dcpa_nm",
                        "tcpa_min",
                        "relative_speed_knots",
                        "relative_bearing_deg",
                        "bearing_abs_deg",
                        "course_difference_deg",
                        "encounter_type",
                        "rule_score",
                        "rule_component_distance",
                        "rule_component_dcpa",
                        "rule_component_tcpa",
                        "rule_component_bearing",
                        "rule_component_relspeed",
                        "rule_component_encounter",
                        "rule_component_density",
                        "future_min_distance_nm",
                        "future_time_to_min_min",
                        "future_points_used",
                        "label_future_conflict",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-03-16T09:00:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": "440000101",
                        "own_segment_id": "440000001-0001",
                        "target_segment_id": "440000101-0001",
                        "own_vessel_type": "tug",
                        "target_vessel_type": "cargo",
                        "own_is_interpolated": "0",
                        "target_is_interpolated": "0",
                        "local_target_count": "3",
                        "distance_nm": "1.000000",
                        "dcpa_nm": "0.500000",
                        "tcpa_min": "4.000000",
                        "relative_speed_knots": "8.000000",
                        "relative_bearing_deg": "45.000000",
                        "bearing_abs_deg": "45.000000",
                        "course_difference_deg": "60.000000",
                        "encounter_type": "crossing",
                        "rule_score": "0.400000",
                        "rule_component_distance": "0.100000",
                        "rule_component_dcpa": "0.100000",
                        "rule_component_tcpa": "0.100000",
                        "rule_component_bearing": "0.050000",
                        "rule_component_relspeed": "0.025000",
                        "rule_component_encounter": "0.015000",
                        "rule_component_density": "0.010000",
                        "future_min_distance_nm": "0.700000",
                        "future_time_to_min_min": "5.000000",
                        "future_points_used": "4",
                        "label_future_conflict": "0",
                    }
                )

            summary = run_pairwise_perturbation(
                input_csv_path=pairwise_path,
                output_prefix=output_prefix,
                config_path=config_path,
                profile_name="position50m",
                position_jitter_m=50.0,
                speed_jitter_frac=0.10,
                course_jitter_deg=5.0,
                drop_rate=0.0,
                random_seed=42,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, int(summary["output_rows"]))
            self.assertGreater(float(summary["mean_abs_distance_delta_nm"]), 0.0)
            self.assertTrue(Path(summary["perturbed_csv_path"]).exists())

            with Path(summary["perturbed_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(1, len(rows))
            self.assertNotEqual("1.000000", rows[0]["distance_nm"])
            self.assertNotEqual("45.000000", rows[0]["relative_bearing_deg"])
            self.assertNotEqual("0.400000", rows[0]["rule_score"])


if __name__ == "__main__":
    unittest.main()
