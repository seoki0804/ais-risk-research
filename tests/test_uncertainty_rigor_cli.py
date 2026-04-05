from __future__ import annotations

import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.uncertainty_rigor_cli import main


class UncertaintyRigorCliTest(unittest.TestCase):
    def test_cli_runs_wilson_and_conformal_compare(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            calibration_path = root / "calibration_predictions.csv"
            target_path = root / "target_predictions.csv"
            output_prefix = root / "rigor"

            fieldnames = [
                "timestamp",
                "own_mmsi",
                "target_mmsi",
                "label_future_conflict",
                "hgbt_score",
                "hgbt_pred",
            ]
            calibration_rows = [
                {"timestamp": "c1", "own_mmsi": "1", "target_mmsi": "11", "label_future_conflict": "0", "hgbt_score": "0.10", "hgbt_pred": "0"},
                {"timestamp": "c2", "own_mmsi": "1", "target_mmsi": "12", "label_future_conflict": "1", "hgbt_score": "0.85", "hgbt_pred": "1"},
                {"timestamp": "c3", "own_mmsi": "1", "target_mmsi": "13", "label_future_conflict": "0", "hgbt_score": "0.20", "hgbt_pred": "0"},
                {"timestamp": "c4", "own_mmsi": "1", "target_mmsi": "14", "label_future_conflict": "1", "hgbt_score": "0.75", "hgbt_pred": "1"},
            ]
            target_rows = [
                {"timestamp": "t1", "own_mmsi": "2", "target_mmsi": "21", "label_future_conflict": "0", "hgbt_score": "0.15", "hgbt_pred": "0"},
                {"timestamp": "t2", "own_mmsi": "2", "target_mmsi": "22", "label_future_conflict": "1", "hgbt_score": "0.80", "hgbt_pred": "1"},
            ]

            for path, rows in ((calibration_path, calibration_rows), (target_path, target_rows)):
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

            stdout = io.StringIO()
            argv = [
                "uncertainty_rigor_cli",
                "--calibration-predictions",
                str(calibration_path),
                "--target-predictions",
                str(target_path),
                "--output-prefix",
                str(output_prefix),
                "--models",
                "hgbt",
            ]
            with patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            output = stdout.getvalue()
            self.assertIn("status=completed", output)
            self.assertTrue((root / "rigor_val_calibration_summary.json").exists())
            self.assertTrue((root / "rigor_wilson_summary.json").exists())
            self.assertTrue((root / "rigor_split_conformal_summary.json").exists())
            self.assertTrue((root / "rigor_compare_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
