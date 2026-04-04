from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.unseen_area_evidence_report_cli import main


class UnseenAreaEvidenceReportCliTest(unittest.TestCase):
    def test_cli_invokes_unseen_area_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_run_unseen_area_evidence_report(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "detail_csv_path": str(root / "detail.csv"),
                    "summary_csv_path": str(root / "summary.csv"),
                    "summary_md_path": str(root / "summary.md"),
                    "summary_json_path": str(root / "summary.json"),
                }

            argv = [
                "unseen_area_evidence_report_cli",
                "--true-area-pairwise-summaries",
                f"{root}/a.json,{root}/b.json",
                "--transfer-summaries",
                f"{root}/c.json,{root}/d.json",
                "--output-prefix",
                str(root / "unseen_report"),
                "--min-test-positive-support",
                "7",
                "--target-model",
                "hgbt",
                "--comparator-model",
                "logreg",
            ]

            stdout = io.StringIO()
            with patch(
                "ais_risk.unseen_area_evidence_report_cli.run_unseen_area_evidence_report",
                side_effect=fake_run_unseen_area_evidence_report,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            output = stdout.getvalue()
            self.assertIn("detail_csv=", output)
            self.assertIn("summary_csv=", output)
            self.assertEqual(str(root / "unseen_report"), captured_kwargs["output_prefix"])
            self.assertEqual(7, captured_kwargs["min_test_positive_support"])
            self.assertEqual(2, len(captured_kwargs["true_area_pairwise_summary_json_paths"]))
            self.assertEqual(2, len(captured_kwargs["transfer_summary_json_paths"]))


if __name__ == "__main__":
    unittest.main()
