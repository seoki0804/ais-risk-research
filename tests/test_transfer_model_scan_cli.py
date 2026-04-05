from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.transfer_model_scan_cli import main


class TransferModelScanCliTest(unittest.TestCase):
    def test_cli_invokes_scan_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_transfer_model_scan(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                out = root / "scan"
                return {
                    "summary_md_path": str(out.with_suffix(".md")),
                    "summary_json_path": str(out.with_suffix(".json")),
                    "detail_csv_path": str(out.with_name(out.name + "_detail").with_suffix(".csv")),
                    "model_summary_csv_path": str(out.with_name(out.name + "_model_summary").with_suffix(".csv")),
                    "recommended_model": "hgbt",
                }

            argv = [
                "transfer_model_scan_cli",
                "--source-region",
                "houston",
                "--source-input",
                str(root / "houston.csv"),
                "--targets",
                f"nola:{root / 'nola.csv'},seattle:{root / 'seattle.csv'}",
                "--output-root",
                str(root / "out"),
                "--models",
                "hgbt,extra_trees",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.transfer_model_scan_cli.run_transfer_model_scan",
                side_effect=fake_run_transfer_model_scan,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("recommended_model=hgbt", stdout.getvalue())
            self.assertEqual("houston", captured_kwargs["source_region"])
            self.assertEqual({"nola", "seattle"}, set(captured_kwargs["target_input_paths_by_region"].keys()))


if __name__ == "__main__":
    unittest.main()
