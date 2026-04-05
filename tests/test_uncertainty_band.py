from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.uncertainty_band import run_uncertainty_band


class UncertaintyBandTest(unittest.TestCase):
    def test_run_uncertainty_band_generates_sample_level_bands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            predictions_path = root / "predictions.csv"
            bins_path = root / "calibration_bins.csv"
            output_prefix = root / "uncertainty_band"

            with predictions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "timestamp",
                        "own_mmsi",
                        "target_mmsi",
                        "label_future_conflict",
                        "logreg_score",
                        "logreg_pred",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000101",
                            "label_future_conflict": "1",
                            "logreg_score": "0.85",
                            "logreg_pred": "1",
                        },
                        {
                            "timestamp": "2026-03-16T09:01:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000102",
                            "label_future_conflict": "0",
                            "logreg_score": "0.15",
                            "logreg_pred": "0",
                        },
                        {
                            "timestamp": "2026-03-16T09:02:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000103",
                            "label_future_conflict": "1",
                            "logreg_score": "0.95",
                            "logreg_pred": "1",
                        },
                    ]
                )

            with bins_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "model",
                        "bin_index",
                        "bin_lower",
                        "bin_upper",
                        "count",
                        "avg_score",
                        "empirical_rate",
                        "gap_abs",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "model": "logreg",
                            "bin_index": "1",
                            "bin_lower": "0.1",
                            "bin_upper": "0.2",
                            "count": "10",
                            "avg_score": "0.15",
                            "empirical_rate": "0.10",
                            "gap_abs": "0.05",
                        },
                        {
                            "model": "logreg",
                            "bin_index": "8",
                            "bin_lower": "0.8",
                            "bin_upper": "0.9",
                            "count": "20",
                            "avg_score": "0.85",
                            "empirical_rate": "0.75",
                            "gap_abs": "0.10",
                        },
                    ]
                )

            summary = run_uncertainty_band(
                predictions_csv_path=predictions_path,
                calibration_bins_csv_path=bins_path,
                output_prefix=output_prefix,
                confidence_level=0.95,
            )

            self.assertEqual("completed", summary["status"])
            self.assertIn("logreg", summary["model_names"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["sample_bands_csv_path"]).exists())
            self.assertEqual(3, int(summary["models"]["logreg"]["sample_count"]))
            self.assertEqual(1, int(summary["models"]["logreg"]["fallback_rows"]))

            with Path(summary["sample_bands_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(3, len(rows))
            self.assertEqual("0.750000", rows[0]["score_mean"])
            self.assertEqual("0.100000", rows[1]["score_mean"])
            self.assertEqual("fallback_raw_score", rows[2]["band_status"])
            self.assertEqual("0.950000", rows[2]["score_mean"])


if __name__ == "__main__":
    unittest.main()
