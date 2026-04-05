from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.regional_gradcam_report_cli import main


class RegionalGradcamReportCliTest(unittest.TestCase):
    def test_cli_prints_created_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            benchmark_summary_json = root / "benchmark_summary.json"
            benchmark_summary_json.write_text(json.dumps({"ok": True}), encoding="utf-8")

            def fake_run_regional_gradcam_report(**_: object) -> dict[str, object]:
                summary_json = root / "gradcam_summary.json"
                summary_md = root / "gradcam_summary.md"
                figure_png = root / "gradcam_figure.png"
                figure_svg = root / "gradcam_figure.svg"
                summary_json.write_text(json.dumps({"status": "completed"}), encoding="utf-8")
                summary_md.write_text("# ok\n", encoding="utf-8")
                figure_png.write_bytes(b"png")
                figure_svg.write_text("<svg />", encoding="utf-8")
                return {
                    "summary_json_path": str(summary_json),
                    "summary_md_path": str(summary_md),
                    "figure_png_path": str(figure_png),
                    "figure_svg_path": str(figure_svg),
                }

            argv = [
                "regional_gradcam_report_cli",
                "--benchmark-summary-json",
                str(benchmark_summary_json),
                "--output-prefix",
                str(root / "gradcam"),
                "--torch-device",
                "cpu",
            ]
            with patch("ais_risk.regional_gradcam_report_cli.run_regional_gradcam_report", side_effect=fake_run_regional_gradcam_report), patch(
                "sys.argv", argv
            ):
                main()

            self.assertTrue((root / "gradcam_summary.json").exists())
            self.assertTrue((root / "gradcam_summary.md").exists())
            self.assertTrue((root / "gradcam_figure.png").exists())
            self.assertTrue((root / "gradcam_figure.svg").exists())


if __name__ == "__main__":
    unittest.main()
