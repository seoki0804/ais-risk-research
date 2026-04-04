from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.error_taxonomy_report_cli import main


class ErrorTaxonomyReportCliTest(unittest.TestCase):
    def test_cli_invokes_taxonomy_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "out"
            captured_kwargs: dict[str, object] = {}

            def fake_run_error_taxonomy_for_recommended_models(**kwargs: object) -> dict[str, object]:
                captured_kwargs.update(kwargs)
                output_root.mkdir(parents=True, exist_ok=True)
                return {
                    "summary_json_path": str(output_root / "summary.json"),
                    "summary_md_path": str(output_root / "summary.md"),
                    "summary_csv_path": str(output_root / "summary.csv"),
                    "taxonomy_csv_path": str(output_root / "taxonomy.csv"),
                }

            argv = [
                "error_taxonomy_report_cli",
                "--input-dir",
                str(root),
                "--regions",
                "houston,nola",
                "--recommendation-csv",
                str(root / "recommendation.csv"),
                "--run-manifest-csv",
                str(root / "manifest.csv"),
                "--output-root",
                str(output_root),
                "--seed",
                "42",
            ]
            stdout = io.StringIO()
            with patch(
                "ais_risk.error_taxonomy_report_cli.run_error_taxonomy_for_recommended_models",
                side_effect=fake_run_error_taxonomy_for_recommended_models,
            ), patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            self.assertIn("summary_json=", stdout.getvalue())
            self.assertEqual(42, captured_kwargs["seed"])
            self.assertEqual({"houston", "nola"}, set(captured_kwargs["input_paths_by_region"].keys()))


if __name__ == "__main__":
    unittest.main()
