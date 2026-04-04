from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.reliability_report_cli import main


class ReliabilityReportCliTest(unittest.TestCase):
    def test_cli_invokes_reliability_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "out"
            captured_kwargs: dict[str, object] = {}

            def fake_run_reliability_report_for_recommended_models(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                output_root.mkdir(parents=True, exist_ok=True)
                return {
                    "summary_json_path": str(output_root / "summary.json"),
                    "summary_md_path": str(output_root / "summary.md"),
                    "region_summary_csv_path": str(output_root / "region_summary.csv"),
                    "region_bins_csv_path": str(output_root / "bins.csv"),
                }

            argv = [
                "reliability_report_cli",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--run-manifest-csv",
                str(root / "manifest.csv"),
                "--output-root",
                str(output_root),
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.reliability_report_cli.run_reliability_report_for_recommended_models",
                side_effect=fake_run_reliability_report_for_recommended_models,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_json=", stdout.getvalue())
            self.assertEqual(str(root / "recommendation.csv"), captured_kwargs["recommendation_csv_path"])


if __name__ == "__main__":
    unittest.main()
