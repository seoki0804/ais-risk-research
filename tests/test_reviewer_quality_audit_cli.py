from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.reviewer_quality_audit_cli import main


class ReviewerQualityAuditCliTest(unittest.TestCase):
    def test_cli_invokes_audit_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_reviewer_quality_audit(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_json_path": str(root / "audit.json"),
                    "summary_md_path": str(root / "audit.md"),
                }

            argv = [
                "reviewer_quality_audit_cli",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--aggregate-csv",
                str(root / "aggregate.csv"),
                "--winner-summary-csv",
                str(root / "winner.csv"),
                "--out-of-time-csv",
                str(root / "oot.csv"),
                "--transfer-csv",
                str(root / "transfer.csv"),
                "--reliability-region-summary-csv",
                str(root / "reliability.csv"),
                "--taxonomy-region-summary-csv",
                str(root / "taxonomy.csv"),
                "--output-prefix",
                str(root / "audit"),
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.reviewer_quality_audit_cli.run_reviewer_quality_audit",
                side_effect=fake_run_reviewer_quality_audit,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_json=", stdout.getvalue())
            self.assertEqual(str(root / "recommendation.csv"), captured_kwargs["recommendation_csv_path"])
            self.assertEqual(str(root / "audit"), captured_kwargs["output_prefix"])


if __name__ == "__main__":
    unittest.main()
