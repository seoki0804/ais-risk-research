from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.unseen_area_evidence_report import run_unseen_area_evidence_report


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_predictions(path: Path, labels: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["label_future_conflict"])
        writer.writeheader()
        for label in labels:
            writer.writerow({"label_future_conflict": int(label)})


class UnseenAreaEvidenceReportTest(unittest.TestCase):
    def test_generates_true_area_and_transfer_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            alpha_dir = root / "alpha_pooled"
            beta_dir = root / "beta_pooled"
            alpha_pairwise = alpha_dir / "alpha_pooled_pairwise_summary.json"
            beta_pairwise = beta_dir / "beta_pooled_pairwise_summary.json"

            _write_json(alpha_pairwise, {"output_rows": 100})
            _write_json(beta_pairwise, {"output_rows": 80})

            for region, directory, own_f1, ts_f1, own_labels, ts_labels in [
                ("alpha", alpha_dir, 0.62, 0.57, [1] * 8 + [0] * 12, [1] * 6 + [0] * 10),
                ("beta", beta_dir, 0.20, 0.00, [1] * 1 + [0] * 19, [1] * 0 + [0] * 16),
            ]:
                _write_json(
                    directory / f"{region}_pooled_own_ship_summary.json",
                    {
                        "row_count": 120,
                        "positive_rate": 0.08,
                        "own_ship_count": 6,
                        "models": {
                            "hgbt": {"f1": own_f1, "auroc": 0.90, "auprc": 0.50, "threshold": 0.3},
                            "logreg": {"f1": max(0.0, own_f1 - 0.1), "threshold": 0.8},
                        },
                    },
                )
                _write_json(
                    directory / f"{region}_pooled_timestamp_summary.json",
                    {
                        "row_count": 120,
                        "positive_rate": 0.08,
                        "own_ship_count": 6,
                        "models": {
                            "hgbt": {"f1": ts_f1, "auroc": 0.88, "auprc": 0.45, "threshold": 0.25},
                            "logreg": {"f1": max(0.0, ts_f1 - 0.08), "threshold": 0.9},
                        },
                    },
                )
                _write_predictions(directory / f"{region}_pooled_own_ship_test_predictions.csv", own_labels)
                _write_predictions(directory / f"{region}_pooled_timestamp_test_predictions.csv", ts_labels)

            transfer_a = root / "alpha_2023_to_2024_transfer_summary.json"
            transfer_b = root / "beta_2024_to_2023_transfer_summary.json"
            _write_json(
                transfer_a,
                {
                    "target_row_count": 300,
                    "target_positive_rate": 0.11,
                    "target_own_ship_count": 7,
                    "split": {"strategy": "own_ship"},
                    "models": {
                        "hgbt": {"threshold": 0.3, "source_test": {"f1": 0.70}, "target_transfer": {"f1": 0.66, "auroc": 0.92, "auprc": 0.64}},
                        "logreg": {"threshold": 0.8, "source_test": {"f1": 0.62}, "target_transfer": {"f1": 0.60}},
                    },
                    "target_predictions_csv_path": str(root / "alpha_target_predictions.csv"),
                },
            )
            _write_json(
                transfer_b,
                {
                    "target_row_count": 250,
                    "target_positive_rate": 0.05,
                    "target_own_ship_count": 5,
                    "split": {"strategy": "own_ship"},
                    "models": {
                        "hgbt": {"threshold": 0.2, "source_test": {"f1": 0.45}, "target_transfer": {"f1": 0.50, "auroc": 0.81, "auprc": 0.30}},
                        "logreg": {"threshold": 0.7, "source_test": {"f1": 0.40}, "target_transfer": {"f1": 0.39}},
                    },
                    "target_predictions_csv_path": str(root / "beta_target_predictions.csv"),
                },
            )

            output_prefix = root / "unseen_area_report"
            summary = run_unseen_area_evidence_report(
                true_area_pairwise_summary_json_paths=[alpha_pairwise, beta_pairwise],
                transfer_summary_json_paths=[transfer_a, transfer_b],
                output_prefix=output_prefix,
                min_test_positive_support=5,
                target_model="hgbt",
                comparator_model="logreg",
            )

            self.assertEqual("completed", summary["status"])
            self.assertTrue(Path(summary["detail_csv_path"]).exists())
            self.assertTrue(Path(summary["summary_csv_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())

            detail_rows = list(csv.DictReader(Path(summary["detail_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(6, len(detail_rows))
            true_rows = [row for row in detail_rows if row["evidence_type"] == "true_unseen_area"]
            transfer_rows = [row for row in detail_rows if row["evidence_type"] == "cross_year_transfer"]
            self.assertEqual(4, len(true_rows))
            self.assertEqual(2, len(transfer_rows))

            summary_rows = list(csv.DictReader(Path(summary["summary_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(1, len(summary_rows))
            row = summary_rows[0]
            self.assertEqual("2", row["true_area_region_count"])
            self.assertEqual("2", row["true_area_low_support_count"])
            self.assertEqual("1", row["transfer_negative_delta_count"])
            self.assertIn("beta:own_ship", row["low_support_region_splits"])

            md_text = Path(summary["summary_md_path"]).read_text(encoding="utf-8")
            self.assertIn("True Unseen-Area Evidence Report", md_text)
            self.assertIn("Cross-Year Transfer Snapshot", md_text)


if __name__ == "__main__":
    unittest.main()
