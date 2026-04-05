from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import build_snapshot_from_curated_csv, load_curated_csv_rows, preprocess_ais_csv


class CsvToolsTest(unittest.TestCase):
    def test_preprocess_normalizes_headers(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sample_input = root / "examples" / "sample_ais.csv"
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "curated.csv"
            stats = preprocess_ais_csv(sample_input, output_path)

            self.assertEqual(stats["rejected_rows"], 0)
            self.assertEqual(stats["output_rows"], 13)
            with output_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(
                    reader.fieldnames,
                    ["mmsi", "timestamp", "lat", "lon", "sog", "cog", "heading", "vessel_type"],
                )

    def test_build_snapshot_filters_by_radius(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sample_input = root / "examples" / "sample_ais.csv"
        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            preprocess_ais_csv(sample_input, curated_path)
            snapshot = build_snapshot_from_curated_csv(
                input_path=curated_path,
                own_mmsi="440000001",
                timestamp="2026-03-07T09:00:00Z",
                radius_nm=6.0,
            )

            self.assertEqual(snapshot.own_ship.mmsi, "440000001")
            self.assertEqual(len(snapshot.targets), 3)
            self.assertNotIn("440000104", {target.mmsi for target in snapshot.targets})

    def test_preprocess_treats_heading_511_as_missing(self) -> None:
        rows = [
            {
                "MMSI": "440000001",
                "BaseDateTime": "2026-03-07T09:00:00",
                "LAT": "35.0500",
                "LON": "129.0500",
                "SOG": "12.0",
                "COG": "45.0",
                "Heading": "511",
                "VesselType": "70",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "sentinel_heading.csv"
            output_path = Path(temp_dir) / "curated.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            stats = preprocess_ais_csv(input_path, output_path)
            curated_rows = load_curated_csv_rows(output_path)

            self.assertEqual(stats["output_rows"], 1)
            self.assertEqual(curated_rows[0]["heading"], "")

    def test_preprocess_rejects_cog_360_sentinel(self) -> None:
        rows = [
            {
                "MMSI": "440000001",
                "BaseDateTime": "2026-03-07T09:00:00",
                "LAT": "35.0500",
                "LON": "129.0500",
                "SOG": "12.0",
                "COG": "360.0",
                "Heading": "45.0",
                "VesselType": "70",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "sentinel_cog.csv"
            output_path = Path(temp_dir) / "curated.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            stats = preprocess_ais_csv(input_path, output_path)

            self.assertEqual(stats["rejected_rows"], 1)
            self.assertEqual(stats["output_rows"], 0)


if __name__ == "__main__":
    unittest.main()
