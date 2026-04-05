from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.external_validity_manuscript_assets_cli import main


class ExternalValidityManuscriptAssetsCliTest(unittest.TestCase):
    def test_cli_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            captured_kwargs: dict[str, object] = {}

            def fake_runner(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                return {
                    "summary_json_path": str(root / "summary.json"),
                    "integration_note_md_path": str(root / "integration.md"),
                    "transfer_uncertainty_table_md_path": str(root / "transfer.md"),
                    "scenario_panels_md_path": str(root / "panels.md"),
                }

            argv = [
                "external_validity_manuscript_assets_cli",
                "--transfer-gap-detail-csv",
                str(root / "transfer_detail.csv"),
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--reliability-region-summary-csv",
                str(root / "reliability.csv"),
                "--taxonomy-region-summary-csv",
                str(root / "taxonomy.csv"),
                "--contour-summary-json-by-region",
                f"houston:{root / 'h.json'},nola:{root / 'n.json'},seattle:{root / 's.json'}",
                "--output-prefix",
                str(root / "assets"),
            ]
            stdout = io.StringIO()
            with patch(
                "ais_risk.external_validity_manuscript_assets_cli.run_external_validity_manuscript_assets",
                side_effect=fake_runner,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_json=", stdout.getvalue())
            self.assertEqual(str(root / "transfer_detail.csv"), captured_kwargs["transfer_gap_detail_csv_path"])
            self.assertEqual(str(root / "recommendation.csv"), captured_kwargs["recommendation_csv_path"])
            mapping = captured_kwargs["contour_report_summary_json_by_region"]
            self.assertIn("houston", mapping)
            self.assertIn("nola", mapping)
            self.assertIn("seattle", mapping)


if __name__ == "__main__":
    unittest.main()
