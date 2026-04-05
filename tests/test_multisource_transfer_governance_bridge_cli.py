from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.multisource_transfer_governance_bridge_cli import main


class MultiSourceTransferGovernanceBridgeCliTest(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_runner(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_md_path": str(root / "bridge.md"),
                    "summary_json_path": str(root / "bridge.json"),
                    "detail_csv_path": str(root / "bridge_detail.csv"),
                }

            argv = [
                "multisource_transfer_governance_bridge_cli",
                "--multisource-source-summary-csv",
                str(root / "source_summary.csv"),
                "--transfer-policy-governance-lock-json",
                str(root / "policy_lock.json"),
                "--output-prefix",
                str(root / "bridge"),
            ]
            stdout = io.StringIO()
            with patch(
                "ais_risk.multisource_transfer_governance_bridge_cli.run_multisource_transfer_governance_bridge",
                side_effect=fake_runner,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            out = stdout.getvalue()
            self.assertIn("summary_md=", out)
            self.assertEqual(str(root / "source_summary.csv"), captured_kwargs["multisource_source_summary_csv_path"])
            self.assertEqual(str(root / "policy_lock.json"), captured_kwargs["transfer_policy_governance_lock_json_path"])
            self.assertEqual(str(root / "bridge"), captured_kwargs["output_prefix"])


if __name__ == "__main__":
    unittest.main()

