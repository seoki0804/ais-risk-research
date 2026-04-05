from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.out_of_time_threshold_policy_compare_cli import main


class OutOfTimeThresholdPolicyCompareCliTest(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_out_of_time_threshold_policy_compare(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_json_path": str(root / "compare.json"),
                    "summary_md_path": str(root / "compare.md"),
                    "detail_csv_path": str(root / "compare_detail.csv"),
                    "policy_summary_csv_path": str(root / "compare_policy_summary.csv"),
                }

            argv = [
                "out_of_time_threshold_policy_compare_cli",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--baseline-leaderboard-csv",
                str(root / "baseline.csv"),
                "--out-of-time-output-root",
                str(root / "oot"),
                "--output-prefix",
                str(root / "compare"),
                "--dataset-prefixes",
                "houston,nola",
                "--threshold-grid-step",
                "0.02",
                "--max-out-of-time-ece",
                "0.11",
                "--min-out-of-time-delta-f1",
                "-0.04",
                "--max-in-time-regression-from-best-f1",
                "0.03",
                "--disable-oracle-policy",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.out_of_time_threshold_policy_compare_cli.run_out_of_time_threshold_policy_compare",
                side_effect=fake_run_out_of_time_threshold_policy_compare,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_json=", stdout.getvalue())
            self.assertEqual(str(root / "recommendation.csv"), captured_kwargs["recommendation_csv_path"])
            self.assertEqual(str(root / "baseline.csv"), captured_kwargs["baseline_leaderboard_csv_path"])
            self.assertEqual(str(root / "oot"), captured_kwargs["out_of_time_output_root"])
            self.assertEqual(str(root / "compare"), captured_kwargs["output_prefix"])
            self.assertEqual(["houston", "nola"], captured_kwargs["dataset_prefix_filters"])
            self.assertEqual(0.02, captured_kwargs["threshold_grid_step"])
            self.assertEqual(0.11, captured_kwargs["max_out_of_time_ece"])
            self.assertEqual(-0.04, captured_kwargs["min_out_of_time_delta_f1"])
            self.assertEqual(0.03, captured_kwargs["max_in_time_regression_from_best_f1"])
            self.assertFalse(bool(captured_kwargs["include_oracle_policy"]))


if __name__ == "__main__":
    unittest.main()
