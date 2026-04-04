from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.threshold_robustness_report_cli import main


class ThresholdRobustnessReportCliTest(unittest.TestCase):
    def test_cli_invokes_threshold_robustness_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_threshold_robustness_report(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "detail_csv_path": str(root / "detail.csv"),
                    "summary_csv_path": str(root / "summary.csv"),
                    "summary_md_path": str(root / "summary.md"),
                    "summary_json_path": str(root / "summary.json"),
                }

            argv = [
                "threshold_robustness_report_cli",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--run-manifest-csv",
                str(root / "run_manifest.csv"),
                "--output-prefix",
                str(root / "threshold_robustness"),
                "--cost-profiles",
                "balanced:1:1,fn_heavy:1:3",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.threshold_robustness_report_cli.run_threshold_robustness_report",
                side_effect=fake_run_threshold_robustness_report,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            output = stdout.getvalue()
            self.assertIn("detail_csv=", output)
            self.assertIn("summary_md=", output)
            self.assertEqual(str(root / "recommendation.csv"), captured_kwargs["recommendation_csv_path"])
            self.assertEqual("balanced:1:1,fn_heavy:1:3", captured_kwargs["cost_profiles"])


if __name__ == "__main__":
    unittest.main()
