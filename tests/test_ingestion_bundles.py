from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ais_risk.ingestion_bundles import (
    get_ingestion_bundle,
    list_ingestion_bundle_names,
    load_ingestion_bundle_config,
    render_ingestion_bundle_toml,
    resolve_ingestion_bundle,
    write_ingestion_bundle_template,
)


class IngestionBundleTest(unittest.TestCase):
    def test_bundle_registry_and_rendering_work(self) -> None:
        names = list_ingestion_bundle_names()
        self.assertIn("generic_harbor", names)
        bundle = get_ingestion_bundle("shipid_xy_demo")
        toml_text = render_ingestion_bundle_toml(bundle)
        self.assertIn('source_preset = "shipid_eventtime_xy"', toml_text)
        self.assertIn('"cargo"', toml_text)

    def test_resolve_ingestion_bundle_supplies_defaults_and_allows_override(self) -> None:
        resolved = resolve_ingestion_bundle(
            bundle_name="shipid_xy_demo",
            config_path=None,
            source_preset_name="auto",
            manual_column_map_text="heading=HeadingDeg",
            vessel_types_text="cargo,tanker",
        )
        self.assertEqual(resolved["source_preset"], "shipid_eventtime_xy")
        self.assertEqual(resolved["vessel_types"], ("cargo", "tanker"))
        self.assertIn("heading=HeadingDeg", resolved["column_map_text"])

    def test_write_ingestion_bundle_template_saves_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "bundle.toml"
            write_ingestion_bundle_template("verbose_port_mix", output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("verbose_port_mix", output_path.read_text(encoding="utf-8"))

    def test_load_ingestion_bundle_config_reads_template_file(self) -> None:
        bundle = load_ingestion_bundle_config("configs/ingestion/marinecadastre_harbor.toml")
        self.assertEqual(bundle.name, "marinecadastre_harbor")
        self.assertEqual(bundle.source_preset, "marinecadastre_like")
        self.assertIn("cargo", bundle.vessel_types)

    def test_config_path_takes_precedence_over_named_bundle(self) -> None:
        resolved = resolve_ingestion_bundle(
            bundle_name="generic_harbor",
            config_path="configs/ingestion/shipid_xy_demo.toml",
            source_preset_name="auto",
            manual_column_map_text="heading=HeadingDeg",
            vessel_types_text="",
        )
        self.assertEqual(resolved["bundle_name"], "shipid_xy_demo")
        self.assertEqual(resolved["source_preset"], "shipid_eventtime_xy")
        self.assertEqual(resolved["bundle_config_path"], "configs/ingestion/shipid_xy_demo.toml")
        self.assertIn("heading=HeadingDeg", resolved["column_map_text"])


if __name__ == "__main__":
    unittest.main()
