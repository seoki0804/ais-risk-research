from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import load_curated_csv_rows, preprocess_ais_csv
from ais_risk.vessel_types import normalize_vessel_type


class VesselTypeTest(unittest.TestCase):
    def test_normalize_vessel_type_handles_numeric_and_textual_inputs(self) -> None:
        self.assertEqual(normalize_vessel_type("70"), "cargo")
        self.assertEqual(normalize_vessel_type("Cargo Vessel"), "cargo")
        self.assertEqual(normalize_vessel_type("80"), "tanker")
        self.assertEqual(normalize_vessel_type("Passenger"), "passenger")
        self.assertEqual(normalize_vessel_type("52"), "tug")
        self.assertEqual(normalize_vessel_type("31"), "towing")
        self.assertEqual(normalize_vessel_type(""), "")

    def test_preprocess_standardizes_vessel_type_and_filter(self) -> None:
        rows = [
            {
                "MMSI": "440000001",
                "BaseDateTime": "2026-03-07T09:00:00Z",
                "LAT": "35.0500",
                "LON": "129.0500",
                "SOG": "12.0",
                "COG": "45.0",
                "Heading": "45.0",
                "VesselType": "70",
            },
            {
                "MMSI": "440000002",
                "BaseDateTime": "2026-03-07T09:00:00Z",
                "LAT": "35.0600",
                "LON": "129.0600",
                "SOG": "11.0",
                "COG": "220.0",
                "Heading": "220.0",
                "VesselType": "Passenger vessel",
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "raw.csv"
            output_path = Path(temp_dir) / "curated.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            stats = preprocess_ais_csv(input_path, output_path, allowed_vessel_types={"cargo"})
            curated_rows = load_curated_csv_rows(output_path)

            self.assertEqual(stats["output_rows"], 1)
            self.assertEqual(curated_rows[0]["vessel_type"], "cargo")


if __name__ == "__main__":
    unittest.main()
