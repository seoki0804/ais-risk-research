from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.significance_report_cli import main


class SignificanceReportCliTest(unittest.TestCase):
    def test_cli_invokes_significance_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_significance_report(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "csv_path": str(root / "significance.csv"),
                    "md_path": str(root / "significance.md"),
                    "json_path": str(root / "significance.json"),
                }

            argv = [
                "significance_report_cli",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--raw-rows-csv",
                str(root / "raw_rows.csv"),
                "--output-prefix",
                str(root / "significance"),
                "--bootstrap-samples",
                "100",
                "--bootstrap-seed",
                "11",
                "--min-pairs",
                "4",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.significance_report_cli.run_significance_report",
                side_effect=fake_run_significance_report,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            output = stdout.getvalue()
            self.assertIn("csv=", output)
            self.assertIn("md=", output)
            self.assertIn("json=", output)
            self.assertEqual(str(root / "recommendation.csv"), captured_kwargs["recommendation_csv_path"])
            self.assertEqual(100, captured_kwargs["bootstrap_samples"])


if __name__ == "__main__":
    unittest.main()
