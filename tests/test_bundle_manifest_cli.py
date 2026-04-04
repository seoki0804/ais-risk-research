from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.bundle_manifest_cli import main


class BundleManifestCliTest(unittest.TestCase):
    def test_cli_builds_manifest_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle_dir = root / "bundle"
            bundle_dir.mkdir(parents=True, exist_ok=True)
            (bundle_dir / "a.csv").write_text("id,value\n1,10\n", encoding="utf-8")
            source_dir = root / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
            input_csv = root / "input.csv"
            input_csv.write_text("x\n1\n", encoding="utf-8")
            command_log = root / "commands.log"
            command_log.write_text("echo test\n", encoding="utf-8")

            manifest_txt = bundle_dir / "bundle_manifest_2026-04-04-expanded.txt"
            manifest_json = bundle_dir / "bundle_manifest_2026-04-04-expanded.json"
            argv = [
                "bundle_manifest_cli",
                "--bundle-date",
                "2026-04-04-expanded",
                "--bundle-dir",
                str(bundle_dir),
                "--copied-file",
                "a.csv",
                "--source-dir",
                f"main={source_dir}",
                "--input-file",
                str(input_csv),
                "--command-log",
                str(command_log),
                "--manifest-txt",
                str(manifest_txt),
                "--manifest-json",
                str(manifest_json),
            ]

            stdout = io.StringIO()
            with patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            output = stdout.getvalue()
            self.assertIn("manifest_txt=", output)
            self.assertIn("manifest_json=", output)
            self.assertTrue(manifest_txt.exists())
            self.assertTrue(manifest_json.exists())


if __name__ == "__main__":
    unittest.main()
