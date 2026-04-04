from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.benchmark import _feature_dict, run_pairwise_benchmark

try:
    import torch  # type: ignore
except Exception:  # pragma: no cover
    torch = None


class BenchmarkTest(unittest.TestCase):
    def test_feature_dict_excludes_future_only_support_fields(self) -> None:
        payload = _feature_dict(
            {
                "distance_nm": "1.0",
                "dcpa_nm": "0.5",
                "tcpa_min": "2.0",
                "relative_speed_knots": "10.0",
                "relative_bearing_deg": "15.0",
                "bearing_abs_deg": "15.0",
                "course_difference_deg": "20.0",
                "local_target_count": "3",
                "rule_score": "0.8",
                "rule_component_distance": "0.1",
                "rule_component_dcpa": "0.1",
                "rule_component_tcpa": "0.1",
                "rule_component_bearing": "0.1",
                "rule_component_relspeed": "0.1",
                "rule_component_encounter": "0.1",
                "rule_component_density": "0.1",
                "future_points_used": "7",
                "encounter_type": "crossing",
                "own_vessel_type": "cargo",
                "target_vessel_type": "tanker",
                "own_is_interpolated": "0",
                "target_is_interpolated": "1",
            }
        )
        self.assertNotIn("future_points_used", payload)

    def test_pairwise_benchmark_generates_summary_and_predictions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_path = tmp_path / "pairwise.csv"
            output_prefix = tmp_path / "benchmark"

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
            for index in range(9):
                positive = 1 if index % 3 == 0 else 0
                rows.append(
                    {
                        "timestamp": f"2026-03-07T09:{index:02d}:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": f"4400001{index:02d}",
                        "own_segment_id": "440000001-0001",
                        "target_segment_id": f"4400001{index:02d}-0001",
                        "own_vessel_type": "cargo",
                        "target_vessel_type": "cargo" if positive else "tanker",
                        "own_is_interpolated": "0",
                        "target_is_interpolated": "0",
                        "local_target_count": "3",
                        "distance_nm": "0.200000" if positive else "3.000000",
                        "dcpa_nm": "0.100000" if positive else "2.500000",
                        "tcpa_min": "3.000000" if positive else "18.000000",
                        "relative_speed_knots": "12.000000" if positive else "4.000000",
                        "relative_bearing_deg": "10.000000" if positive else "130.000000",
                        "bearing_abs_deg": "10.000000" if positive else "130.000000",
                        "course_difference_deg": "170.000000" if positive else "20.000000",
                        "encounter_type": "head_on" if positive else "diverging",
                        "rule_score": "0.920000" if positive else "0.150000",
                        "rule_component_distance": "0.200000",
                        "rule_component_dcpa": "0.200000",
                        "rule_component_tcpa": "0.200000",
                        "rule_component_bearing": "0.100000",
                        "rule_component_relspeed": "0.070000",
                        "rule_component_encounter": "0.100000",
                        "rule_component_density": "0.050000",
                        "future_min_distance_nm": "0.150000" if positive else "2.200000",
                        "future_time_to_min_min": "2.000000" if positive else "10.000000",
                        "future_points_used": "4",
                        "label_future_conflict": str(positive),
                    }
                )

            with dataset_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            summary = run_pairwise_benchmark(
                input_path=dataset_path,
                output_prefix=output_prefix,
                model_names=["rule_score", "logreg", "hgbt", "random_forest", "extra_trees"],
            )

            self.assertIn("models", summary)
            self.assertIn("logreg", summary["models"])
            self.assertIn("random_forest", summary["models"])
            self.assertIn("extra_trees", summary["models"])
            self.assertEqual("timestamp", summary["split"]["strategy"])
            self.assertIn("benchmark_elapsed_seconds", summary)
            self.assertIn("elapsed_seconds", summary["models"]["rule_score"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["predictions_csv_path"]).exists())

    def test_pairwise_benchmark_supports_own_ship_holdout_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_path = tmp_path / "pairwise.csv"
            output_prefix = tmp_path / "benchmark_own_ship"

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
            own_ships = ["440000001", "440000002", "440000003"]
            for ship_index, own_mmsi in enumerate(own_ships):
                for index in range(6):
                    positive = 1 if index % 2 == 0 else 0
                    rows.append(
                        {
                            "timestamp": f"2026-03-07T0{ship_index}:{index:02d}:00Z",
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

            summary = run_pairwise_benchmark(
                input_path=dataset_path,
                output_prefix=output_prefix,
                model_names=["rule_score", "logreg"],
                split_strategy="own_ship",
            )

            self.assertEqual("own_ship", summary["split"]["strategy"])
            self.assertEqual(1, summary["split"]["test_own_ships"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())

    @unittest.skipIf(torch is None, "PyTorch is not installed")
    def test_pairwise_benchmark_torch_mlp_is_reproducible_with_fixed_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_path = tmp_path / "pairwise.csv"
            output_prefix_a = tmp_path / "benchmark_a"
            output_prefix_b = tmp_path / "benchmark_b"

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
            for index in range(15):
                positive = 1 if index % 2 == 0 else 0
                rows.append(
                    {
                        "timestamp": f"2026-03-07T09:{index:02d}:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": f"4400002{index:02d}",
                        "own_segment_id": "440000001-0001",
                        "target_segment_id": f"4400002{index:02d}-0001",
                        "own_vessel_type": "cargo",
                        "target_vessel_type": "cargo" if positive else "tanker",
                        "own_is_interpolated": "0",
                        "target_is_interpolated": "0",
                        "local_target_count": "3",
                        "distance_nm": "0.250000" if positive else "2.800000",
                        "dcpa_nm": "0.120000" if positive else "2.200000",
                        "tcpa_min": "3.500000" if positive else "16.500000",
                        "relative_speed_knots": "11.500000" if positive else "4.500000",
                        "relative_bearing_deg": "15.000000" if positive else "145.000000",
                        "bearing_abs_deg": "15.000000" if positive else "145.000000",
                        "course_difference_deg": "168.000000" if positive else "22.000000",
                        "encounter_type": "head_on" if positive else "diverging",
                        "rule_score": "0.900000" if positive else "0.160000",
                        "rule_component_distance": "0.200000",
                        "rule_component_dcpa": "0.200000",
                        "rule_component_tcpa": "0.200000",
                        "rule_component_bearing": "0.100000",
                        "rule_component_relspeed": "0.070000",
                        "rule_component_encounter": "0.100000",
                        "rule_component_density": "0.050000",
                        "future_min_distance_nm": "0.180000" if positive else "2.050000",
                        "future_time_to_min_min": "2.800000" if positive else "9.800000",
                        "future_points_used": "4",
                        "label_future_conflict": str(positive),
                    }
                )

            with dataset_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            summary_a = run_pairwise_benchmark(
                input_path=dataset_path,
                output_prefix=output_prefix_a,
                model_names=["torch_mlp"],
                torch_device="cpu",
                random_seed=123,
            )
            summary_b = run_pairwise_benchmark(
                input_path=dataset_path,
                output_prefix=output_prefix_b,
                model_names=["torch_mlp"],
                torch_device="cpu",
                random_seed=123,
            )

            self.assertEqual(123, summary_a.get("random_seed"))
            self.assertEqual(123, summary_b.get("random_seed"))
            self.assertAlmostEqual(
                float(summary_a["models"]["torch_mlp"]["f1"]),
                float(summary_b["models"]["torch_mlp"]["f1"]),
                places=8,
            )

            def _read_scores(path: str) -> list[float]:
                with Path(path).open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    return [float(row["torch_mlp_score"]) for row in reader]

            scores_a = _read_scores(summary_a["predictions_csv_path"])
            scores_b = _read_scores(summary_b["predictions_csv_path"])
            self.assertEqual(len(scores_a), len(scores_b))
            for left, right in zip(scores_a, scores_b):
                self.assertAlmostEqual(left, right, places=8)


if __name__ == "__main__":
    unittest.main()
