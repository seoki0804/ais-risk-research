from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.regional_raster_cnn_cli import main


class RegionalRasterCnnCliTest(unittest.TestCase):
    def test_cli_writes_summary_from_stubbed_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "pairwise.csv"
            with input_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["timestamp", "own_mmsi", "target_mmsi", "label_future_conflict"])
                writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": "2026-03-16T09:00:00Z",
                        "own_mmsi": "440000001",
                        "target_mmsi": "440000101",
                        "label_future_conflict": "1",
                    }
                )

            output_prefix = root / "regional_cnn"

            def fake_run_regional_raster_cnn_benchmark(**_: object) -> dict[str, object]:
                summary_json = root / "regional_cnn_summary.json"
                summary_md = root / "regional_cnn_summary.md"
                predictions_csv = root / "regional_cnn_predictions.csv"
                summary_json.write_text(json.dumps({"status": "completed"}), encoding="utf-8")
                summary_md.write_text("# ok\n", encoding="utf-8")
                predictions_csv.write_text("timestamp,cnn_score\n", encoding="utf-8")
                return {
                    "summary_json_path": str(summary_json),
                    "summary_md_path": str(summary_md),
                    "predictions_csv_path": str(predictions_csv),
                }

            argv = [
                "regional_raster_cnn_cli",
                "--input",
                str(input_csv),
                "--output-prefix",
                str(output_prefix),
                "--epochs",
                "2",
                "--max-train-rows",
                "8",
            ]
            with patch("ais_risk.regional_raster_cnn_cli.run_regional_raster_cnn_benchmark", side_effect=fake_run_regional_raster_cnn_benchmark), patch(
                "sys.argv", argv
            ):
                main()

            self.assertTrue((root / "regional_cnn_summary.json").exists())
            self.assertTrue((root / "regional_cnn_summary.md").exists())
            self.assertTrue((root / "regional_cnn_predictions.csv").exists())


if __name__ == "__main__":
    unittest.main()
