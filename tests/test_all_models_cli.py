from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.all_models_cli import main


class AllModelsCliTest(unittest.TestCase):
    def test_cli_passes_arguments_to_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "pairwise.csv"
            input_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            output_dir = root / "out"
            summary = {
                "summary_json_path": str(output_dir / "summary.json"),
                "summary_md_path": str(output_dir / "summary.md"),
                "leaderboard_csv_path": str(output_dir / "leaderboard.csv"),
                "leaderboard_md_path": str(output_dir / "leaderboard.md"),
            }

            argv = [
                "all_models_cli",
                "--input",
                str(input_csv),
                "--output-dir",
                str(output_dir),
                "--split-strategy",
                "timestamp",
                "--include-regional-cnn",
                "--cnn-losses",
                "weighted_bce,focal",
                "--cnn-no-balanced-batches",
                "--cnn-max-train-rows",
                "128",
                "--cnn-max-val-rows",
                "64",
                "--cnn-max-test-rows",
                "32",
            ]

            with patch("ais_risk.all_models_cli.run_all_supported_models", return_value=summary) as run_mock, patch("sys.argv", argv):
                main()

            kwargs = run_mock.call_args.kwargs
            self.assertEqual(str(input_csv), kwargs["input_path"])
            self.assertEqual(str(output_dir), kwargs["output_dir"])
            self.assertEqual("timestamp", kwargs["split_strategy"])
            self.assertTrue(kwargs["include_regional_cnn"])
            self.assertEqual(["weighted_bce", "focal"], kwargs["cnn_losses"])
            self.assertFalse(kwargs["cnn_balance_batches"])
            self.assertEqual(128, kwargs["cnn_max_train_rows"])
            self.assertEqual(64, kwargs["cnn_max_val_rows"])
            self.assertEqual(32, kwargs["cnn_max_test_rows"])


if __name__ == "__main__":
    unittest.main()
