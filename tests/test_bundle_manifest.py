from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.bundle_manifest import build_bundle_manifest


class BundleManifestTest(unittest.TestCase):
    def test_build_bundle_manifest_writes_hashes_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle_dir = root / "bundle"
            bundle_dir.mkdir(parents=True, exist_ok=True)
            (bundle_dir / "a.csv").write_text("id,value\n1,10\n", encoding="utf-8")
            (bundle_dir / "b.md").write_text("# report\n", encoding="utf-8")

            source_multi = root / "source_multi"
            source_seed = root / "source_seed"
            source_multi.mkdir(parents=True, exist_ok=True)
            source_seed.mkdir(parents=True, exist_ok=True)

            input_csv = root / "input.csv"
            input_csv.write_text("x\n1\n", encoding="utf-8")
            command_log = root / "commands.log"
            command_log.write_text("python -m ais_risk.foo\n", encoding="utf-8")

            summary = build_bundle_manifest(
                bundle_date="2026-04-04-expanded",
                bundle_dir=bundle_dir,
                copied_files=["a.csv", "b.md"],
                source_dirs={"multiarea": source_multi, "seed_sweep": source_seed},
                input_files=[input_csv],
                command_logs=[command_log, root / "missing.log"],
            )

            manifest_txt_path = Path(summary["manifest_txt_path"])
            manifest_json_path = Path(summary["manifest_json_path"])
            self.assertTrue(manifest_txt_path.exists())
            self.assertTrue(manifest_json_path.exists())
            self.assertEqual(2, int(summary["copied_file_count"]))
            self.assertEqual(1, int(summary["input_file_count"]))
            self.assertEqual(2, int(summary["command_log_count"]))

            payload = json.loads(manifest_json_path.read_text(encoding="utf-8"))
            self.assertEqual("2026-04-04-expanded", payload["bundle_date"])
            self.assertEqual(2, len(payload["copied_files"]))
            self.assertEqual(1, len(payload["input_files"]))
            self.assertEqual(2, len(payload["command_logs"]))
            self.assertEqual(False, bool(payload["command_logs"][1]["exists"]))
            self.assertEqual(64, len(str(payload["copied_files"][0]["sha256"])))

    def test_build_bundle_manifest_raises_when_copied_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle_dir = root / "bundle"
            bundle_dir.mkdir(parents=True, exist_ok=True)
            with self.assertRaises(FileNotFoundError):
                build_bundle_manifest(
                    bundle_date="2026-04-04-expanded",
                    bundle_dir=bundle_dir,
                    copied_files=["missing.csv"],
                    source_dirs={},
                )


if __name__ == "__main__":
    unittest.main()
