from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.uncertainty_interval_compare import run_uncertainty_interval_compare


class UncertaintyIntervalCompareTest(unittest.TestCase):
    def test_compares_two_interval_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline_a = root / "wilson.csv"
            baseline_b = root / "conformal.csv"
            output_prefix = root / "compare"

            fieldnames = [
                "timestamp",
                "own_mmsi",
                "target_mmsi",
                "label_future_conflict",
                "model",
                "score_lower",
                "score_upper",
            ]
            with baseline_a.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(
                    [
                        {"timestamp": "t1", "own_mmsi": "1", "target_mmsi": "11", "label_future_conflict": "0", "model": "hgbt", "score_lower": "0.0", "score_upper": "0.3"},
                        {"timestamp": "t2", "own_mmsi": "1", "target_mmsi": "12", "label_future_conflict": "1", "model": "hgbt", "score_lower": "0.7", "score_upper": "1.0"},
                    ]
                )
            with baseline_b.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(
                    [
                        {"timestamp": "t1", "own_mmsi": "1", "target_mmsi": "11", "label_future_conflict": "0", "model": "hgbt", "score_lower": "0.0", "score_upper": "0.6"},
                        {"timestamp": "t2", "own_mmsi": "1", "target_mmsi": "12", "label_future_conflict": "1", "model": "hgbt", "score_lower": "0.4", "score_upper": "1.0"},
                    ]
                )

            summary = run_uncertainty_interval_compare(
                baseline_a_csv_path=baseline_a,
                baseline_b_csv_path=baseline_b,
                output_prefix=output_prefix,
            )

            self.assertEqual("completed", summary["status"])
            self.assertTrue((root / "compare_summary.json").exists())
            self.assertTrue((root / "compare_rows.csv").exists())
            self.assertEqual(2, len(summary["rows"]))


if __name__ == "__main__":
    unittest.main()
