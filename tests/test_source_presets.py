from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import load_curated_csv_rows, preprocess_ais_csv
from ais_risk.schema_probe import inspect_csv_schema
from ais_risk.source_presets import get_source_preset, list_source_preset_names, resolve_source_preset


class SourcePresetTest(unittest.TestCase):
    def test_source_preset_registry_exposes_expected_presets(self) -> None:
        names = list_source_preset_names()
        self.assertIn("auto", names)
        self.assertIn("shipid_eventtime_xy", names)
        self.assertIn("noaa_accessais", names)
        self.assertEqual(get_source_preset("marinecadastre_like").name, "marinecadastre_like")

    def test_shipid_eventtime_xy_preset_supports_probe_and_preprocess(self) -> None:
        rows = [
            {
                "ShipId": "440000001",
                "Event Time": "2026-03-07 09:00:00",
                "Y": "35.0500",
                "X": "129.0500",
                "Speed": "12.0",
                "Course": "45.0",
                "ShipCategory": "Cargo vessel",
            },
            {
                "ShipId": "440000002",
                "Event Time": "2026-03-07 09:01:00",
                "Y": "35.0600",
                "X": "129.0600",
                "Speed": "10.0",
                "Course": "220.0",
                "ShipCategory": "80",
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "custom.csv"
            output_path = Path(temp_dir) / "curated.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            overrides = resolve_source_preset("shipid_eventtime_xy")
            probe = inspect_csv_schema(input_path, column_overrides=overrides)
            stats = preprocess_ais_csv(input_path, output_path, column_overrides=overrides)
            curated_rows = load_curated_csv_rows(output_path)

            self.assertTrue(probe["ready_for_preprocess"])
            self.assertEqual(probe["detected_mapping"]["mmsi"], "ShipId")
            self.assertEqual(stats["output_rows"], 2)
            self.assertEqual(curated_rows[0]["vessel_type"], "cargo")
            self.assertEqual(curated_rows[1]["vessel_type"], "tanker")

    def test_manual_override_takes_priority_over_preset(self) -> None:
        overrides = resolve_source_preset(
            "shipid_eventtime_xy",
            "vessel_type=TypeLabel,heading=HeadingDeg",
        )
        self.assertEqual(overrides["vessel_type"], "TypeLabel")
        self.assertEqual(overrides["heading"], "HeadingDeg")
        self.assertEqual(overrides["mmsi"], "ShipId")


if __name__ == "__main__":
    unittest.main()
