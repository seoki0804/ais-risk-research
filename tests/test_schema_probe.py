from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import load_curated_csv_rows, parse_column_overrides, preprocess_ais_csv
from ais_risk.schema_probe import inspect_csv_schema


class SchemaProbeTest(unittest.TestCase):
    def test_schema_probe_detects_alternative_headers(self) -> None:
        rows = [
            {
                "Ship MMSI": "440000001",
                "Base Date Time": "2026-03-07 09:00:00",
                "LATITUDE": "35.0500",
                "LONGITUDE": "129.0500",
                "Speed Over Ground": "12.0",
                "Course Over Ground": "45.0",
                "True Heading": "45.0",
                "Ship Type": "cargo",
            },
            {
                "Ship MMSI": "440000002",
                "Base Date Time": "2026-03-07 09:00:00",
                "LATITUDE": "35.0600",
                "LONGITUDE": "129.0600",
                "Speed Over Ground": "10.5",
                "Course Over Ground": "220.0",
                "True Heading": "220.0",
                "Ship Type": "tanker",
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "alt_headers.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            probe = inspect_csv_schema(input_path)

            self.assertTrue(probe["ready_for_preprocess"])
            self.assertEqual(probe["detected_mapping"]["mmsi"], "Ship MMSI")
            self.assertEqual(probe["detected_mapping"]["timestamp"], "Base Date Time")
            self.assertEqual(probe["detected_mapping"]["sog"], "Speed Over Ground")
            self.assertEqual(probe["detected_mapping"]["vessel_type"], "Ship Type")
            self.assertEqual(probe["field_quality"]["vessel_type"]["standardized_values"][0], "cargo")

    def test_preprocess_supports_alternative_headers(self) -> None:
        rows = [
            {
                "Ship MMSI": "440000001",
                "Base Date Time": "2026/03/07 09:00:00",
                "LATITUDE": "35.0500",
                "LONGITUDE": "129.0500",
                "Speed Over Ground": "12.0",
                "Course Over Ground": "45.0",
                "True Heading": "45.0",
                "Ship Type": "cargo",
            },
            {
                "Ship MMSI": "440000001",
                "Base Date Time": "2026/03/07 09:02:00",
                "LATITUDE": "35.0510",
                "LONGITUDE": "129.0510",
                "Speed Over Ground": "12.1",
                "Course Over Ground": "46.0",
                "True Heading": "46.0",
                "Ship Type": "cargo",
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "alt_headers.csv"
            output_path = Path(temp_dir) / "curated.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            stats = preprocess_ais_csv(input_path, output_path)
            curated_rows = load_curated_csv_rows(output_path)

            self.assertEqual(stats["output_rows"], 2)
            self.assertEqual(curated_rows[0]["mmsi"], "440000001")
            self.assertEqual(curated_rows[0]["timestamp"], "2026-03-07T09:00:00Z")
            self.assertEqual(curated_rows[0]["vessel_type"], "cargo")

    def test_schema_probe_and_preprocess_support_column_overrides(self) -> None:
        rows = [
            {
                "ShipId": "440000001",
                "Event Time": "2026-03-07 09:00:00",
                "Y": "35.0500",
                "X": "129.0500",
                "Speed": "12.0",
                "Course": "45.0",
            },
            {
                "ShipId": "440000002",
                "Event Time": "2026-03-07 09:01:00",
                "Y": "35.0600",
                "X": "129.0600",
                "Speed": "10.0",
                "Course": "220.0",
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "custom_headers.csv"
            output_path = Path(temp_dir) / "curated.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            overrides = parse_column_overrides("mmsi=ShipId,timestamp=Event Time,lat=Y,lon=X,sog=Speed,cog=Course")
            probe_without_override = inspect_csv_schema(input_path)
            probe_with_override = inspect_csv_schema(input_path, column_overrides=overrides)
            stats = preprocess_ais_csv(input_path, output_path, column_overrides=overrides)
            curated_rows = load_curated_csv_rows(output_path)

            self.assertFalse(probe_without_override["ready_for_preprocess"])
            self.assertTrue(probe_with_override["ready_for_preprocess"])
            self.assertEqual(probe_with_override["detected_mapping"]["mmsi"], "ShipId")
            self.assertEqual(stats["output_rows"], 2)
            self.assertIn("mmsi:ShipId", stats["resolved_columns"])
            self.assertEqual(curated_rows[0]["mmsi"], "440000001")

    def test_schema_probe_marks_heading_511_as_invalid(self) -> None:
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
            },
            {
                "MMSI": "440000001",
                "BaseDateTime": "2026-03-07T09:01:00",
                "LAT": "35.0501",
                "LON": "129.0501",
                "SOG": "12.0",
                "COG": "46.0",
                "Heading": "46.0",
                "VesselType": "70",
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "heading_probe.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            probe = inspect_csv_schema(input_path)

            self.assertTrue(probe["ready_for_preprocess"])
            self.assertEqual(probe["field_quality"]["heading"]["non_empty_ratio"], 1.0)
            self.assertLess(probe["field_quality"]["heading"]["valid_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
