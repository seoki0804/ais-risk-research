from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.transfer_override_seed_stress_test_cli import main


class TransferOverrideSeedStressTestCli(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_runner(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_md_path": str(root / "stress.md"),
                    "summary_json_path": str(root / "stress.json"),
                    "per_seed_csv_path": str(root / "stress_per_seed.csv"),
                    "run_root": str(root / "runs"),
                }

            argv = [
                "transfer_override_seed_stress_test_cli",
                "--input-dir",
                str(root / "input"),
                "--output-prefix",
                str(root / "stress"),
                "--source-region",
                "houston",
                "--target-regions",
                "nola,seattle",
                "--baseline-model",
                "hgbt",
                "--override-model",
                "rule_score",
                "--override-method",
                "isotonic",
                "--seeds",
                "41,42,43",
                "--split-strategy",
                "own_ship",
                "--train-fraction",
                "0.6",
                "--val-fraction",
                "0.2",
                "--threshold-grid-step",
                "0.01",
                "--ece-gate-max",
                "0.10",
                "--max-negative-pairs-allowed",
                "1",
                "--torch-device",
                "auto",
                "--calibration-bins",
                "10",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.transfer_override_seed_stress_test_cli.run_transfer_override_seed_stress_test",
                side_effect=fake_runner,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            out = stdout.getvalue()
            self.assertIn("summary_md=", out)
            self.assertIn("per_seed_csv=", out)
            self.assertEqual(str(root / "input"), captured_kwargs["input_dir"])
            self.assertEqual(str(root / "stress"), captured_kwargs["output_prefix"])
            self.assertEqual("houston", captured_kwargs["source_region"])
            self.assertEqual(["nola", "seattle"], captured_kwargs["target_regions"])
            self.assertEqual("hgbt", captured_kwargs["baseline_model"])
            self.assertEqual("rule_score", captured_kwargs["override_model"])
            self.assertEqual("isotonic", captured_kwargs["override_method"])
            self.assertEqual("41,42,43", captured_kwargs["random_seeds"])


if __name__ == "__main__":
    unittest.main()

