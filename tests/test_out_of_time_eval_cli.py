from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.out_of_time_eval_cli import main


class OutOfTimeEvalCliTest(unittest.TestCase):
    def test_cli_invokes_out_of_time_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "out"
            captured_kwargs: dict[str, object] = {}

            def fake_run_out_of_time_recommendation_check(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                output_root.mkdir(parents=True, exist_ok=True)
                return {
                    "summary_json_path": str(output_root / "summary.json"),
                    "results_csv_path": str(output_root / "results.csv"),
                    "results_md_path": str(output_root / "results.md"),
                }

            argv = [
                "out_of_time_eval_cli",
                "--input-dir",
                str(root),
                "--output-root",
                str(output_root),
                "--regions",
                "houston,nola",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--baseline-leaderboard-csv",
                str(root / "baseline.csv"),
            ]

            stdout = io.StringIO()
            with patch("ais_risk.out_of_time_eval_cli.run_out_of_time_recommendation_check", side_effect=fake_run_out_of_time_recommendation_check), patch(
                "sys.argv", argv
            ):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_json=", stdout.getvalue())
            self.assertEqual({"houston", "nola"}, set(captured_kwargs["input_paths_by_region"].keys()))
            self.assertEqual("timestamp", captured_kwargs["split_strategy"])


if __name__ == "__main__":
    unittest.main()
