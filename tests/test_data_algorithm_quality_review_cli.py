from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.data_algorithm_quality_review_cli import main


class DataAlgorithmQualityReviewCliTest(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_runner(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_md_path": str(root / "quality.md"),
                    "summary_json_path": str(root / "quality.json"),
                    "dataset_scorecard_csv_path": str(root / "quality_dataset_scorecard.csv"),
                    "high_risk_models_csv_path": str(root / "quality_high_risk_models.csv"),
                    "todo_csv_path": str(root / "quality_todo.csv"),
                }

            argv = [
                "data_algorithm_quality_review_cli",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--aggregate-csv",
                str(root / "aggregate.csv"),
                "--out-of-time-csv",
                str(root / "out_of_time.csv"),
                "--transfer-csv",
                str(root / "transfer.csv"),
                "--output-prefix",
                str(root / "quality"),
                "--out-of-time-threshold-policy-compare-json",
                str(root / "oot_policy_compare.json"),
                "--multisource-transfer-governance-bridge-json",
                str(root / "bridge.json"),
                "--transfer-override-seed-stress-test-json",
                str(root / "override_seed_stress.json"),
                "--manuscript-freeze-packet-json",
                str(root / "manuscript_freeze_packet.json"),
                "--min-positive-support",
                "35",
                "--max-ece",
                "0.09",
                "--max-f1-std",
                "0.02",
                "--min-out-of-time-delta-f1",
                "-0.04",
                "--max-negative-transfer-pairs",
                "0",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.data_algorithm_quality_review_cli.run_data_algorithm_quality_review",
                side_effect=fake_runner,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            out = stdout.getvalue()
            self.assertIn("summary_md=", out)
            self.assertIn("todo_csv=", out)
            self.assertEqual(str(root / "recommendation.csv"), captured_kwargs["recommendation_csv_path"])
            self.assertEqual(str(root / "aggregate.csv"), captured_kwargs["aggregate_csv_path"])
            self.assertEqual(str(root / "out_of_time.csv"), captured_kwargs["out_of_time_csv_path"])
            self.assertEqual(str(root / "transfer.csv"), captured_kwargs["transfer_csv_path"])
            self.assertEqual(str(root / "quality"), captured_kwargs["output_prefix"])
            self.assertEqual(
                str(root / "oot_policy_compare.json"),
                captured_kwargs["out_of_time_threshold_policy_compare_json_path"],
            )
            self.assertEqual(str(root / "bridge.json"), captured_kwargs["multisource_transfer_governance_bridge_json_path"])
            self.assertEqual(
                str(root / "override_seed_stress.json"),
                captured_kwargs["transfer_override_seed_stress_test_json_path"],
            )
            self.assertEqual(
                str(root / "manuscript_freeze_packet.json"),
                captured_kwargs["manuscript_freeze_packet_json_path"],
            )
            self.assertEqual(35, captured_kwargs["min_positive_support"])
            self.assertEqual(0.09, captured_kwargs["max_ece"])
            self.assertEqual(0.02, captured_kwargs["max_f1_std"])
            self.assertEqual(-0.04, captured_kwargs["min_out_of_time_delta_f1"])
            self.assertEqual(0, captured_kwargs["max_negative_transfer_pairs"])


if __name__ == "__main__":
    unittest.main()
