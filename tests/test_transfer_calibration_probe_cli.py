from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.transfer_calibration_probe_cli import main


class TransferCalibrationProbeCliTest(unittest.TestCase):
    def test_cli_invokes_probe_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_transfer_calibration_probe(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_json_path": str(root / "probe.json"),
                    "summary_md_path": str(root / "probe.md"),
                    "detail_csv_path": str(root / "probe_detail.csv"),
                    "model_method_summary_csv_path": str(root / "probe_model_method_summary.csv"),
                }

            argv = [
                "transfer_calibration_probe_cli",
                "--transfer-scan-detail-csv",
                str(root / "detail.csv"),
                "--output-prefix",
                str(root / "probe"),
                "--source-region",
                "houston",
                "--models",
                "hgbt,rule_score",
                "--methods",
                "none,platt",
                "--threshold-grid-step",
                "0.02",
                "--ece-gate-max",
                "0.11",
                "--max-negative-pairs-allowed",
                "1",
                "--random-seed",
                "7",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.transfer_calibration_probe_cli.run_transfer_calibration_probe",
                side_effect=fake_run_transfer_calibration_probe,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_json=", stdout.getvalue())
            self.assertEqual(str(root / "detail.csv"), captured_kwargs["transfer_scan_detail_csv_path"])
            self.assertEqual(str(root / "probe"), captured_kwargs["output_prefix"])
            self.assertEqual("houston", captured_kwargs["source_region_filter"])
            self.assertEqual(["hgbt", "rule_score"], captured_kwargs["model_names"])
            self.assertEqual(["none", "platt"], captured_kwargs["methods"])
            self.assertEqual(0.02, captured_kwargs["threshold_grid_step"])
            self.assertEqual(0.11, captured_kwargs["ece_gate_max"])
            self.assertEqual(1, captured_kwargs["max_negative_pairs_allowed"])
            self.assertEqual(7, captured_kwargs["random_seed"])


if __name__ == "__main__":
    unittest.main()

