from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.multisource_transfer_model_scan_summary_cli import main


class MultiSourceTransferModelScanSummaryCliTest(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_runner(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_md_path": str(root / "summary.md"),
                    "summary_json_path": str(root / "summary.json"),
                    "detail_csv_path": str(root / "summary_detail.csv"),
                    "source_summary_csv_path": str(root / "summary_source.csv"),
                }

            argv = [
                "multisource_transfer_model_scan_summary_cli",
                "--scan-output-root",
                str(root / "scan"),
                "--source-regions",
                "alpha,beta",
                "--output-prefix",
                str(root / "summary"),
                "--max-target-ece",
                "0.15",
                "--max-negative-pairs",
                "2",
            ]
            stdout = io.StringIO()
            with patch(
                "ais_risk.multisource_transfer_model_scan_summary_cli.run_multisource_transfer_model_scan_summary",
                side_effect=fake_runner,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            out = stdout.getvalue()
            self.assertIn("summary_md=", out)
            self.assertEqual(str(root / "scan"), captured_kwargs["scan_output_root"])
            self.assertEqual(["alpha", "beta"], captured_kwargs["source_regions"])
            self.assertEqual(0.15, captured_kwargs["max_target_ece"])
            self.assertEqual(2, captured_kwargs["max_negative_pairs_allowed"])


if __name__ == "__main__":
    unittest.main()

