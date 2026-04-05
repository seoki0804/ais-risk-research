from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.own_ship_case_eval import run_own_ship_case_evaluation


class OwnShipCaseEvalTest(unittest.TestCase):
    def test_run_own_ship_case_evaluation_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dataset_path = root / "pairwise.csv"
            output_prefix = root / "own_ship_case_eval"

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

            rows: list[dict[str, str]] = []
            own_ships = ["440000001", "440000002", "440000003"]
            for ship_index, own_mmsi in enumerate(own_ships):
                for t_index in range(9):
                    for target_index in range(2):
                        positive = 1 if (t_index + target_index) % 3 == 0 else 0
                        rows.append(
                            {
                                "timestamp": f"2026-03-08T0{ship_index}:{t_index:02d}:00Z",
                                "own_mmsi": own_mmsi,
                                "target_mmsi": f"440001{ship_index}{target_index:02d}",
                                "own_segment_id": f"{own_mmsi}-0001",
                                "target_segment_id": f"440001{ship_index}{target_index:02d}-0001",
                                "own_vessel_type": "cargo",
                                "target_vessel_type": "tanker",
                                "own_is_interpolated": "0",
                                "target_is_interpolated": "0",
                                "local_target_count": "3",
                                "distance_nm": "0.280000" if positive else "2.700000",
                                "dcpa_nm": "0.120000" if positive else "2.200000",
                                "tcpa_min": "4.500000" if positive else "16.000000",
                                "relative_speed_knots": "12.000000" if positive else "4.500000",
                                "relative_bearing_deg": "15.000000" if positive else "135.000000",
                                "bearing_abs_deg": "15.000000" if positive else "135.000000",
                                "course_difference_deg": "170.000000" if positive else "20.000000",
                                "encounter_type": "head_on" if positive else "diverging",
                                "rule_score": "0.900000" if positive else "0.200000",
                                "rule_component_distance": "0.200000",
                                "rule_component_dcpa": "0.200000",
                                "rule_component_tcpa": "0.200000",
                                "rule_component_bearing": "0.100000",
                                "rule_component_relspeed": "0.070000",
                                "rule_component_encounter": "0.100000",
                                "rule_component_density": "0.050000",
                                "future_min_distance_nm": "0.200000" if positive else "2.000000",
                                "future_time_to_min_min": "2.500000" if positive else "9.500000",
                                "future_points_used": "4",
                                "label_future_conflict": str(positive),
                            }
                        )

            with dataset_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            summary = run_own_ship_case_evaluation(
                input_path=dataset_path,
                output_prefix=output_prefix,
                model_names=["rule_score", "logreg", "hgbt"],
                min_rows_per_ship=10,
                train_fraction=0.6,
                val_fraction=0.2,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(3, summary["evaluated_own_ship_count"])
            self.assertGreaterEqual(summary["completed_own_ship_count"], 1)
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["ship_metrics_csv_path"]).exists())
            self.assertTrue(Path(summary["repeat_metrics_csv_path"]).exists())

    def test_run_own_ship_case_evaluation_repeat_count_generates_repeat_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dataset_path = root / "pairwise.csv"
            output_prefix = root / "own_ship_case_eval_repeat"

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

            rows: list[dict[str, str]] = []
            for t_index in range(12):
                for target_index in range(2):
                    positive = 1 if (t_index + target_index) % 3 == 0 else 0
                    rows.append(
                        {
                            "timestamp": f"2026-03-08T00:{t_index:02d}:00Z",
                            "own_mmsi": "440009999",
                            "target_mmsi": f"440101{target_index:02d}",
                            "own_segment_id": "440009999-0001",
                            "target_segment_id": f"440101{target_index:02d}-0001",
                            "own_vessel_type": "cargo",
                            "target_vessel_type": "tanker",
                            "own_is_interpolated": "0",
                            "target_is_interpolated": "0",
                            "local_target_count": "3",
                            "distance_nm": "0.300000" if positive else "2.900000",
                            "dcpa_nm": "0.100000" if positive else "2.100000",
                            "tcpa_min": "4.000000" if positive else "18.000000",
                            "relative_speed_knots": "11.000000" if positive else "4.000000",
                            "relative_bearing_deg": "20.000000" if positive else "140.000000",
                            "bearing_abs_deg": "20.000000" if positive else "140.000000",
                            "course_difference_deg": "168.000000" if positive else "24.000000",
                            "encounter_type": "head_on" if positive else "diverging",
                            "rule_score": "0.900000" if positive else "0.200000",
                            "rule_component_distance": "0.200000",
                            "rule_component_dcpa": "0.200000",
                            "rule_component_tcpa": "0.200000",
                            "rule_component_bearing": "0.100000",
                            "rule_component_relspeed": "0.070000",
                            "rule_component_encounter": "0.100000",
                            "rule_component_density": "0.050000",
                            "future_min_distance_nm": "0.200000" if positive else "2.200000",
                            "future_time_to_min_min": "2.200000" if positive else "11.000000",
                            "future_points_used": "4",
                            "label_future_conflict": str(positive),
                        }
                    )

            with dataset_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            summary = run_own_ship_case_evaluation(
                input_path=dataset_path,
                output_prefix=output_prefix,
                model_names=["rule_score", "logreg"],
                own_mmsis=["440009999"],
                min_rows_per_ship=10,
                train_fraction=0.6,
                val_fraction=0.2,
                repeat_count=3,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, summary["completed_own_ship_count"])
            self.assertEqual(3, summary["repeat_count"])
            self.assertEqual(3, summary["completed_repeats_total"])
            self.assertTrue(Path(summary["repeat_metrics_csv_path"]).exists())

            ship = summary["ships"][0]
            self.assertEqual(3, ship["repeat_count"])
            self.assertEqual(3, ship["completed_repeat_count"])
            self.assertEqual(3, len(ship["repeat_results"]))
            self.assertIn("rule_score", ship["models"])
            self.assertIn("f1_std_repeat", ship["models"]["rule_score"])
            self.assertIn("f1_ci95_low_repeat", ship["models"]["rule_score"])
            self.assertIn("f1_ci95_high_repeat", ship["models"]["rule_score"])
            self.assertIn("f1_ci95_width_repeat", ship["models"]["rule_score"])
            self.assertIn("f1_ci95_low", summary["aggregate_models"]["rule_score"])
            self.assertIn("f1_ci95_high", summary["aggregate_models"]["rule_score"])
            self.assertIn("f1_ci95_width", summary["aggregate_models"]["rule_score"])

    def test_run_own_ship_case_evaluation_filters_requested_own_ships(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dataset_path = root / "pairwise.csv"
            output_prefix = root / "own_ship_case_eval_filter"
            dataset_path.write_text(
                (
                    "timestamp,own_mmsi,target_mmsi,own_segment_id,target_segment_id,own_vessel_type,target_vessel_type,"
                    "own_is_interpolated,target_is_interpolated,local_target_count,distance_nm,dcpa_nm,tcpa_min,relative_speed_knots,"
                    "relative_bearing_deg,bearing_abs_deg,course_difference_deg,encounter_type,rule_score,rule_component_distance,"
                    "rule_component_dcpa,rule_component_tcpa,rule_component_bearing,rule_component_relspeed,rule_component_encounter,"
                    "rule_component_density,future_min_distance_nm,future_time_to_min_min,future_points_used,label_future_conflict\n"
                    "2026-03-08T00:00:00Z,440000001,440000101,440000001-1,440000101-1,cargo,tanker,0,0,2,0.3,0.1,3,12,10,10,170,head_on,0.9,0.2,0.2,0.2,0.1,0.07,0.1,0.05,0.2,2.0,4,1\n"
                    "2026-03-08T00:01:00Z,440000001,440000102,440000001-1,440000102-1,cargo,tanker,0,0,2,2.5,2.2,15,5,130,130,20,diverging,0.2,0.2,0.2,0.2,0.1,0.07,0.1,0.05,2.0,10.0,4,0\n"
                    "2026-03-08T00:02:00Z,440000001,440000103,440000001-1,440000103-1,cargo,tanker,0,0,2,0.4,0.1,4,11,12,12,168,head_on,0.85,0.2,0.2,0.2,0.1,0.07,0.1,0.05,0.3,3.0,4,1\n"
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                run_own_ship_case_evaluation(
                    input_path=dataset_path,
                    output_prefix=output_prefix,
                    own_mmsis=["999999999"],
                )


if __name__ == "__main__":
    unittest.main()
