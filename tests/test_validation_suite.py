from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.validation_suite import run_validation_suite


class ValidationSuiteTest(unittest.TestCase):
    def test_validation_suite_runs_all_strategies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_path = tmp_path / "pairwise.csv"
            output_prefix = tmp_path / "suite"

            fieldnames = [
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
            ]
            rows = []
            own_ships = ["440000001", "440000002", "440000003", "440000004"]
            for ship_index, own_mmsi in enumerate(own_ships):
                for index in range(8):
                    positive = 1 if index % 2 == 0 else 0
                    rows.append(
                        {
                            "timestamp": f"2026-03-07T{index:02d}:00:00Z",
                            "own_mmsi": own_mmsi,
                            "target_mmsi": f"440001{ship_index}{index:02d}",
                            "own_segment_id": f"{own_mmsi}-0001",
                            "target_segment_id": f"440001{ship_index}{index:02d}-0001",
                            "own_vessel_type": "cargo",
                            "target_vessel_type": "tanker",
                            "own_is_interpolated": "0",
                            "target_is_interpolated": "0",
                            "local_target_count": "3",
                            "distance_nm": "0.300000" if positive else "2.900000",
                            "dcpa_nm": "0.150000" if positive else "2.400000",
                            "tcpa_min": "4.000000" if positive else "17.000000",
                            "relative_speed_knots": "11.000000" if positive else "4.500000",
                            "relative_bearing_deg": "20.000000" if positive else "140.000000",
                            "bearing_abs_deg": "20.000000" if positive else "140.000000",
                            "course_difference_deg": "165.000000" if positive else "25.000000",
                            "encounter_type": "head_on" if positive else "diverging",
                            "rule_score": "0.880000" if positive else "0.180000",
                            "rule_component_distance": "0.200000",
                            "rule_component_dcpa": "0.200000",
                            "rule_component_tcpa": "0.200000",
                            "rule_component_bearing": "0.100000",
                            "rule_component_relspeed": "0.070000",
                            "rule_component_encounter": "0.100000",
                            "rule_component_density": "0.050000",
                            "future_min_distance_nm": "0.200000" if positive else "2.100000",
                            "future_time_to_min_min": "3.000000" if positive else "9.000000",
                            "future_points_used": "4",
                            "label_future_conflict": str(positive),
                        }
                    )

            with dataset_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            summary = run_validation_suite(
                input_path=dataset_path,
                output_prefix=output_prefix,
                model_names=["rule_score", "logreg"],
            )
            self.assertEqual("completed", summary["status"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertEqual("completed", summary["strategies"]["timestamp_split"]["status"])
            self.assertEqual("completed", summary["strategies"]["own_ship_split"]["status"])
            self.assertEqual("completed", summary["strategies"]["own_ship_loo"]["status"])


if __name__ == "__main__":
    unittest.main()
