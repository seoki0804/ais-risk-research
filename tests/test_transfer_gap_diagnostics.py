from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.transfer_gap_diagnostics import run_transfer_gap_diagnostics


class TransferGapDiagnosticsTest(unittest.TestCase):
    def test_builds_gap_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            transfer_check_csv = root / "transfer_check.csv"
            source_pred_csv = root / "source_preds.csv"
            target_pred_csv = root / "target_preds.csv"
            transfer_summary_json = root / "transfer_summary.json"

            with source_pred_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["label_future_conflict", "hgbt_score"])
                writer.writeheader()
                writer.writerows(
                    [
                        {"label_future_conflict": "1", "hgbt_score": "0.90"},
                        {"label_future_conflict": "1", "hgbt_score": "0.80"},
                        {"label_future_conflict": "0", "hgbt_score": "0.20"},
                        {"label_future_conflict": "0", "hgbt_score": "0.10"},
                    ]
                )

            with target_pred_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["label_future_conflict", "hgbt_score"])
                writer.writeheader()
                writer.writerows(
                    [
                        {"label_future_conflict": "1", "hgbt_score": "0.70"},
                        {"label_future_conflict": "1", "hgbt_score": "0.65"},
                        {"label_future_conflict": "0", "hgbt_score": "0.60"},
                        {"label_future_conflict": "0", "hgbt_score": "0.20"},
                    ]
                )

            transfer_summary_json.write_text(
                json.dumps(
                    {
                        "source_test_predictions_csv_path": str(source_pred_csv),
                        "target_predictions_csv_path": str(target_pred_csv),
                    }
                ),
                encoding="utf-8",
            )

            with transfer_check_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "source_region",
                        "target_region",
                        "recommended_model",
                        "status",
                        "threshold",
                        "transfer_summary_json_path",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "source_region": "alpha",
                        "target_region": "beta",
                        "recommended_model": "hgbt",
                        "status": "completed",
                        "threshold": "0.50",
                        "transfer_summary_json_path": str(transfer_summary_json),
                    }
                )

            summary = run_transfer_gap_diagnostics(
                transfer_check_csv_path=transfer_check_csv,
                output_prefix=root / "gap_diag",
                threshold_grid_step=0.01,
                bootstrap_samples=100,
                random_seed=42,
            )

            self.assertEqual("completed", summary["status"])
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["detail_csv_path"]).exists())
            self.assertTrue(Path(summary["summary_csv_path"]).exists())
            self.assertEqual(1, int(summary["pair_count"]))
            self.assertEqual(1, int(summary["completed_pair_count"]))


if __name__ == "__main__":
    unittest.main()
