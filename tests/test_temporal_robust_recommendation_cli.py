from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.temporal_robust_recommendation_cli import main


class TemporalRobustRecommendationCliTest(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_temporal_robust_recommendation(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_md_path": str(root / "summary.md"),
                    "summary_json_path": str(root / "summary.json"),
                    "detail_csv_path": str(root / "detail.csv"),
                    "comparison_csv_path": str(root / "comparison.csv"),
                    "recommendation_csv_path": str(root / "recommendation.csv"),
                }

            argv = [
                "temporal_robust_recommendation_cli",
                "--baseline-aggregate-csv",
                str(root / "baseline.csv"),
                "--out-of-time-aggregate-csv",
                str(root / "oot.csv"),
                "--output-prefix",
                str(root / "temporal"),
                "--dataset-prefixes",
                "houston",
                "--min-out-of-time-delta-f1",
                "-0.04",
            ]
            stdout = io.StringIO()
            with patch(
                "ais_risk.temporal_robust_recommendation_cli.run_temporal_robust_recommendation",
                side_effect=fake_run_temporal_robust_recommendation,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_md=", stdout.getvalue())
            self.assertEqual(str(root / "baseline.csv"), captured_kwargs["baseline_aggregate_csv_path"])
            self.assertEqual(str(root / "oot.csv"), captured_kwargs["out_of_time_aggregate_csv_path"])
            self.assertEqual(["houston"], captured_kwargs["dataset_prefix_filters"])
            self.assertEqual(-0.04, captured_kwargs["min_out_of_time_delta_f1"])


if __name__ == "__main__":
    unittest.main()
