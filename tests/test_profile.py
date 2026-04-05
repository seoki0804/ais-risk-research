from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import load_curated_csv_rows, preprocess_ais_csv
from ais_risk.profile import build_profile_markdown, profile_curated_rows, save_profile_outputs


class ProfileTest(unittest.TestCase):
    def test_profile_reports_basic_dataset_stats(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sample_input = root / "examples" / "sample_ais.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            preprocess_ais_csv(sample_input, curated_path)
            rows = load_curated_csv_rows(curated_path)
            profile = profile_curated_rows(rows, top_n=3)

            self.assertEqual(profile["row_count"], 13)
            self.assertEqual(profile["unique_vessels"], 5)
            self.assertIn("cargo", profile["vessel_type_counts"])
            self.assertIsNotNone(profile["gap_stats_seconds"])

    def test_preprocess_filters_bounds_and_time(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sample_input = root / "examples" / "sample_ais.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "filtered.csv"
            stats = preprocess_ais_csv(
                sample_input,
                curated_path,
                min_lat=35.03,
                max_lat=35.10,
                min_lon=129.03,
                max_lon=129.10,
                start_time="2026-03-07T09:00:00Z",
                end_time="2026-03-07T09:00:00Z",
            )
            self.assertGreater(stats["filtered_by_bounds"], 0)
            self.assertGreater(stats["filtered_by_time"], 0)
            rows = load_curated_csv_rows(curated_path)
            self.assertEqual(len(rows), 4)

    def test_profile_outputs_are_saved(self) -> None:
        profile = {
            "row_count": 2,
            "unique_vessels": 1,
            "time_range": {"start": "2026-03-07T09:00:00Z", "end": "2026-03-07T09:01:00Z"},
            "spatial_extent": {"min_lat": 35.0, "max_lat": 35.1, "min_lon": 129.0, "max_lon": 129.1},
            "speed_stats": {"min_sog": 10.0, "median_sog": 10.5, "max_sog": 11.0},
            "heading_coverage_ratio": 1.0,
            "vessel_type_counts": {"cargo": 2},
            "top_vessels_by_rows": [{"mmsi": "100", "row_count": 2}],
            "gap_stats_seconds": {"min": 60.0, "median": 60.0, "p90": 60.0, "max": 60.0, "count": 1},
            "segment_estimate_count_gap_gt_10min": 0,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir) / "sample"
            json_path, md_path = save_profile_outputs(prefix, profile)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = md_path.read_text(encoding="utf-8")
            self.assertEqual(payload["row_count"], 2)
            self.assertIn("# AIS Dataset Profile", markdown)
            self.assertIn("cargo", build_profile_markdown(profile))


if __name__ == "__main__":
    unittest.main()
