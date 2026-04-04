from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.reviewer_quality_audit import run_reviewer_quality_audit


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class ReviewerQualityAuditTest(unittest.TestCase):
    def test_generates_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            aggregate_csv = root / "aggregate.csv"
            winner_csv = root / "winner_summary.csv"
            oot_csv = root / "oot.csv"
            transfer_csv = root / "transfer.csv"
            reliability_csv = root / "reliability.csv"
            taxonomy_csv = root / "taxonomy.csv"
            output_prefix = root / "audit"

            _write_csv(
                recommendation_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "f1_mean": 0.82,
                        "f1_std": 0.0,
                        "ece_mean": 0.02,
                        "ece_std": 0.0,
                        "ece_gate_enabled": True,
                        "ece_gate_max": 0.10,
                        "gate_status": "pass_within_f1_band",
                    },
                    {
                        "dataset": "seattle_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "extra_trees",
                        "f1_mean": 0.81,
                        "f1_std": 0.03,
                        "ece_mean": 0.03,
                        "ece_std": 0.01,
                        "ece_gate_enabled": True,
                        "ece_gate_max": 0.10,
                        "gate_status": "pass_within_f1_band",
                    },
                ],
            )
            _write_csv(
                aggregate_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "f1_mean": 0.82,
                        "f1_std": 0.0,
                        "f1_ci95": 0.0,
                        "ece_mean": 0.02,
                        "ece_std": 0.0,
                    },
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "cnn_weighted",
                        "f1_mean": 0.81,
                        "f1_std": 0.04,
                        "f1_ci95": 0.02,
                        "ece_mean": 0.18,
                        "ece_std": 0.03,
                    },
                    {
                        "dataset": "seattle_pooled_pairwise",
                        "model_name": "extra_trees",
                        "f1_mean": 0.81,
                        "f1_std": 0.03,
                        "f1_ci95": 0.02,
                        "ece_mean": 0.03,
                        "ece_std": 0.01,
                    },
                ],
            )
            _write_csv(
                winner_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "wins": 9,
                        "total_seeds": 10,
                        "win_rate": 0.9,
                    }
                ],
            )
            _write_csv(
                oot_csv,
                [
                    {
                        "region": "houston",
                        "model_name": "hgbt",
                        "delta_f1": -0.10,
                        "delta_ece": 0.01,
                    },
                    {
                        "region": "seattle",
                        "model_name": "extra_trees",
                        "delta_f1": 0.01,
                        "delta_ece": -0.01,
                    },
                ],
            )
            _write_csv(
                transfer_csv,
                [
                    {
                        "source_region": "houston",
                        "target_region": "seattle",
                        "model_name": "hgbt",
                        "delta_f1": -0.20,
                    },
                    {
                        "source_region": "seattle",
                        "target_region": "houston",
                        "model_name": "extra_trees",
                        "delta_f1": 0.05,
                    },
                ],
            )
            _write_csv(
                reliability_csv,
                [
                    {
                        "region": "houston",
                        "sample_count": 1000,
                        "positive_rate": 0.1,
                    },
                    {
                        "region": "seattle",
                        "sample_count": 500,
                        "positive_rate": 0.2,
                    },
                ],
            )
            _write_csv(
                taxonomy_csv,
                [
                    {
                        "region": "houston",
                        "fp": 2,
                        "fn": 5,
                    },
                    {
                        "region": "seattle",
                        "fp": 1,
                        "fn": 8,
                    },
                ],
            )

            summary = run_reviewer_quality_audit(
                recommendation_csv_path=recommendation_csv,
                aggregate_csv_path=aggregate_csv,
                winner_summary_csv_path=winner_csv,
                out_of_time_csv_path=oot_csv,
                transfer_csv_path=transfer_csv,
                reliability_region_summary_csv_path=reliability_csv,
                taxonomy_region_summary_csv_path=taxonomy_csv,
                output_prefix=output_prefix,
            )

            summary_md = Path(summary["summary_md_path"])
            summary_json = Path(summary["summary_json_path"])
            self.assertTrue(summary_md.exists())
            self.assertTrue(summary_json.exists())
            self.assertTrue(summary["calibration_gate_enabled_for_all"])
            self.assertEqual(1, len(summary["oot_negative_regions"]))
            self.assertEqual(1, len(summary["transfer_negative_pairs"]))
            self.assertGreaterEqual(len(summary["high_variance_candidates"]), 1)

            md_text = summary_md.read_text(encoding="utf-8")
            self.assertIn("Reviewer Quality Audit", md_text)
            self.assertIn("Priority TODO", md_text)
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual("completed", payload["status"])


if __name__ == "__main__":
    unittest.main()
