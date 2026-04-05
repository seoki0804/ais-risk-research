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


class ReviewerQualityAuditMultiSourceAddendumTest(unittest.TestCase):
    def test_includes_multisource_addendum(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            aggregate_csv = root / "aggregate.csv"
            winner_csv = root / "winner.csv"
            oot_csv = root / "oot.csv"
            transfer_csv = root / "transfer.csv"
            reliability_csv = root / "reliability.csv"
            taxonomy_csv = root / "taxonomy.csv"
            multisource_json = root / "multisource_transfer_scan_summary.json"
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
                    }
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
                    }
                ],
            )
            _write_csv(
                winner_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "wins": 10,
                        "total_seeds": 10,
                        "win_rate": 1.0,
                    }
                ],
            )
            _write_csv(
                oot_csv,
                [
                    {
                        "region": "houston",
                        "model_name": "hgbt",
                        "delta_f1": 0.02,
                        "delta_ece": 0.00,
                    }
                ],
            )
            _write_csv(
                transfer_csv,
                [
                    {
                        "source_region": "houston",
                        "target_region": "nola",
                        "model_name": "hgbt",
                        "delta_f1": -0.10,
                    }
                ],
            )
            _write_csv(
                reliability_csv,
                [
                    {
                        "region": "houston",
                        "sample_count": 1000,
                        "positive_rate": 0.10,
                    }
                ],
            )
            _write_csv(
                taxonomy_csv,
                [
                    {
                        "region": "houston",
                        "fp": 2,
                        "fn": 5,
                    }
                ],
            )
            multisource_json.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "source_count": 3,
                        "recommended_combined_pass_count": 2,
                        "best_combined_pass_count": 3,
                        "recommendation_mismatch_count": 1,
                        "source_summary_csv_path": str(root / "source_summary.csv"),
                        "detail_csv_path": str(root / "detail.csv"),
                    }
                ),
                encoding="utf-8",
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
                multisource_transfer_model_scan_summary_json_path=multisource_json,
            )

            payload = json.loads(Path(summary["summary_json_path"]).read_text(encoding="utf-8"))
            self.assertTrue(payload["multisource_transfer_model_scan_summary_present"])
            self.assertEqual(3, payload["multisource_transfer_model_scan_summary"]["source_count"])
            self.assertEqual(1, payload["multisource_transfer_model_scan_summary"]["recommendation_mismatch_count"])
            md_text = Path(summary["summary_md_path"]).read_text(encoding="utf-8")
            self.assertIn("Multi-Source Transfer-Model-Scan Addendum", md_text)


if __name__ == "__main__":
    unittest.main()

