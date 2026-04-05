from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.transfer_policy_governance_lock_cli import main


class TransferPolicyGovernanceLockCliTest(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_transfer_policy_governance_lock(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_json_path": str(root / "lock.json"),
                    "summary_md_path": str(root / "lock.md"),
                    "policy_lock_csv_path": str(root / "lock_policy.csv"),
                    "projected_transfer_check_csv_path": str(root / "projected.csv"),
                    "candidate_summary_csv_path": str(root / "candidates.csv"),
                }

            argv = [
                "transfer_policy_governance_lock_cli",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--transfer-check-csv",
                str(root / "transfer.csv"),
                "--out-of-time-threshold-policy-compare-json",
                str(root / "oot_policy.json"),
                "--transfer-calibration-probe-detail-csv",
                str(root / "calibration_detail.csv"),
                "--output-prefix",
                str(root / "lock"),
                "--source-region-for-transfer-override",
                "houston",
                "--metric-mode",
                "retuned",
                "--max-target-ece",
                "0.11",
                "--max-negative-pairs-allowed",
                "2",
                "--required-out-of-time-policy",
                "fixed_baseline_threshold",
                "--override-model-name",
                "rule_score",
                "--override-method",
                "isotonic",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.transfer_policy_governance_lock_cli.run_transfer_policy_governance_lock",
                side_effect=fake_run_transfer_policy_governance_lock,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_json=", stdout.getvalue())
            self.assertEqual(str(root / "recommendation.csv"), captured_kwargs["recommendation_csv_path"])
            self.assertEqual(str(root / "transfer.csv"), captured_kwargs["transfer_check_csv_path"])
            self.assertEqual(str(root / "oot_policy.json"), captured_kwargs["out_of_time_threshold_policy_compare_json_path"])
            self.assertEqual(str(root / "calibration_detail.csv"), captured_kwargs["transfer_calibration_probe_detail_csv_path"])
            self.assertEqual(str(root / "lock"), captured_kwargs["output_prefix"])
            self.assertEqual("houston", captured_kwargs["source_region_for_transfer_override"])
            self.assertEqual("retuned", captured_kwargs["metric_mode"])
            self.assertEqual(0.11, captured_kwargs["max_target_ece"])
            self.assertEqual(2, captured_kwargs["max_negative_pairs_allowed"])
            self.assertEqual("fixed_baseline_threshold", captured_kwargs["required_out_of_time_policy"])
            self.assertEqual("rule_score", captured_kwargs["override_model_name"])
            self.assertEqual("isotonic", captured_kwargs["override_method"])


if __name__ == "__main__":
    unittest.main()
