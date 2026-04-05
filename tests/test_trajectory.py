from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import preprocess_ais_csv
from ais_risk.trajectory import reconstruct_trajectory_csv, reconstruct_trajectory_rows


class TrajectoryTest(unittest.TestCase):
    def test_reconstruction_adds_interpolated_rows(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sample_input = root / "examples" / "sample_ais.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            tracks_path = Path(temp_dir) / "tracks.csv"
            preprocess_ais_csv(sample_input, curated_path)
            stats = reconstruct_trajectory_csv(
                input_path=curated_path,
                output_path=tracks_path,
                split_gap_minutes=10.0,
                max_interp_gap_minutes=2.0,
                step_seconds=60,
            )
            self.assertGreater(stats["output_rows"], stats["input_rows"])
            with tracks_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertIn("segment_id", rows[0])
            self.assertIn("is_interpolated", rows[0])
            self.assertTrue(any(row["is_interpolated"] == "1" for row in rows))

    def test_large_gap_creates_new_segment(self) -> None:
        rows = [
            {
                "mmsi": "100",
                "timestamp": "2026-03-07T09:00:00Z",
                "lat": "35.000000",
                "lon": "129.000000",
                "sog": "10.000000",
                "cog": "10.000000",
                "heading": "10.000000",
                "vessel_type": "cargo",
            },
            {
                "mmsi": "100",
                "timestamp": "2026-03-07T09:20:00Z",
                "lat": "35.100000",
                "lon": "129.100000",
                "sog": "10.000000",
                "cog": "10.000000",
                "heading": "10.000000",
                "vessel_type": "cargo",
            },
        ]
        reconstructed, stats = reconstruct_trajectory_rows(
            rows=rows,
            split_gap_minutes=10.0,
            max_interp_gap_minutes=2.0,
            step_seconds=60,
        )
        self.assertEqual(stats["segment_count"], 2)
        segment_ids = [row["segment_id"] for row in reconstructed]
        self.assertEqual(segment_ids, ["100-0001", "100-0002"])


if __name__ == "__main__":
    unittest.main()
