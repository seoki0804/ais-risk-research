from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.transfer_gap_diagnostics_cli import main


class TransferGapDiagnosticsCliTest(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_transfer_gap_diagnostics(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_md_path": str(root / "gap.md"),
                    "summary_json_path": str(root / "gap.json"),
                    "detail_csv_path": str(root / "gap_detail.csv"),
                    "summary_csv_path": str(root / "gap_summary.csv"),
                }

            argv = [
                "transfer_gap_diagnostics_cli",
                "--transfer-check-csv",
                str(root / "transfer_check.csv"),
                "--output-prefix",
                str(root / "gap"),
                "--bootstrap-samples",
                "250",
            ]
            stdout = io.StringIO()
            with patch(
                "ais_risk.transfer_gap_diagnostics_cli.run_transfer_gap_diagnostics",
                side_effect=fake_run_transfer_gap_diagnostics,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_md=", stdout.getvalue())
            self.assertEqual(str(root / "transfer_check.csv"), captured_kwargs["transfer_check_csv_path"])
            self.assertEqual(250, captured_kwargs["bootstrap_samples"])


if __name__ == "__main__":
    unittest.main()
