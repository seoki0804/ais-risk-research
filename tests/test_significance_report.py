from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.significance_report import run_significance_report


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class SignificanceReportTest(unittest.TestCase):
    def test_report_computes_pairwise_delta_and_ci(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            raw_rows_csv = root / "raw_rows.csv"
            output_prefix = root / "significance"

            _write_csv(
                recommendation_csv,
                [
                    {"dataset": "alpha_pooled_pairwise", "model_name": "model_a"},
                    {"dataset": "beta_pooled_pairwise", "model_name": "model_x"},
                ],
            )

            raw_rows: list[dict[str, object]] = []
            for seed in [1, 2, 3, 4, 5]:
                raw_rows.append(
                    {
                        "dataset": "alpha_pooled_pairwise",
                        "model_name": "model_a",
                        "seed": seed,
                        "status": "completed",
                        "f1": 0.80 + seed * 0.001,
                        "ece": 0.020,
                    }
                )
                raw_rows.append(
                    {
                        "dataset": "alpha_pooled_pairwise",
                        "model_name": "model_b",
                        "seed": seed,
                        "status": "completed",
                        "f1": 0.75 + seed * 0.001,
                        "ece": 0.050,
                    }
                )
                raw_rows.append(
                    {
                        "dataset": "beta_pooled_pairwise",
                        "model_name": "model_x",
                        "seed": seed,
                        "status": "completed",
                        "f1": 0.70,
                        "ece": 0.030,
                    }
                )
                raw_rows.append(
                    {
                        "dataset": "beta_pooled_pairwise",
                        "model_name": "model_y",
                        "seed": seed,
                        "status": "completed",
                        "f1": 0.69 + (0.002 if seed % 2 else -0.002),
                        "ece": 0.028 + (0.001 if seed % 2 else -0.001),
                    }
                )
            _write_csv(raw_rows_csv, raw_rows)

            summary = run_significance_report(
                recommendation_csv_path=recommendation_csv,
                raw_rows_csv_path=raw_rows_csv,
                output_prefix=output_prefix,
                bootstrap_samples=500,
                bootstrap_seed=7,
                min_pairs=5,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["row_count"])
            csv_path = Path(summary["csv_path"])
            md_path = Path(summary["md_path"])
            json_path = Path(summary["json_path"])
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue(json_path.exists())

            rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8", newline="")))
            alpha = [row for row in rows if row["dataset"] == "alpha_pooled_pairwise"][0]
            self.assertEqual("model_a", alpha["recommended_model"])
            self.assertEqual("model_b", alpha["comparator_model"])
            self.assertEqual("5", alpha["n_pairs"])
            self.assertEqual("True", alpha["f1_rec_better_ci"])
            self.assertEqual("True", alpha["ece_rec_lower_ci"])
            self.assertGreater(float(alpha["delta_f1_mean"]), 0.0)
            self.assertLess(float(alpha["delta_ece_mean"]), 0.0)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(2, len(payload["results"]))

    def test_report_handles_insufficient_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            raw_rows_csv = root / "raw_rows.csv"
            output_prefix = root / "significance"

            _write_csv(recommendation_csv, [{"dataset": "alpha_pooled_pairwise", "model_name": "model_a"}])
            _write_csv(
                raw_rows_csv,
                [
                    {"dataset": "alpha_pooled_pairwise", "model_name": "model_a", "seed": 1, "status": "completed", "f1": 0.8, "ece": 0.02},
                    {"dataset": "alpha_pooled_pairwise", "model_name": "model_b", "seed": 1, "status": "completed", "f1": 0.7, "ece": 0.04},
                ],
            )

            summary = run_significance_report(
                recommendation_csv_path=recommendation_csv,
                raw_rows_csv_path=raw_rows_csv,
                output_prefix=output_prefix,
                min_pairs=3,
            )
            rows = list(csv.DictReader(Path(summary["csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(1, len(rows))
            self.assertIn("insufficient paired seeds", rows[0]["note"])


if __name__ == "__main__":
    unittest.main()
