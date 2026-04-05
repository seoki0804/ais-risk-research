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


class ReviewerQualityAuditDataAlgorithmAddendumTest(unittest.TestCase):
    def test_includes_data_algorithm_addendum(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            aggregate_csv = root / "aggregate.csv"
            winner_csv = root / "winner.csv"
            oot_csv = root / "oot.csv"
            transfer_csv = root / "transfer.csv"
            reliability_csv = root / "reliability.csv"
            taxonomy_csv = root / "taxonomy.csv"
            quality_json = root / "quality_review.json"
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
                        "delta_f1": 0.01,
                        "delta_ece": 0.0,
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
            quality_json.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "dataset_count": 3,
                        "baseline_combined_pass_count": 2,
                        "final_combined_pass_count": 3,
                        "governance_improved_dataset_count": 1,
                        "high_risk_model_count": 5,
                        "todo_count": 4,
                        "dq5_acceptance_met": True,
                        "dataset_scorecard_csv_path": str(root / "dataset_scorecard.csv"),
                        "high_risk_models_csv_path": str(root / "high_risk_models.csv"),
                        "todo_csv_path": str(root / "todo.csv"),
                        "transfer_override_seed_stress_test_present": True,
                        "transfer_override_seed_stress_test_json_path": str(root / "seed_stress.json"),
                        "manuscript_freeze_packet_present": True,
                        "manuscript_freeze_packet_json_path": str(root / "freeze_packet.json"),
                        "manuscript_freeze_packet": {
                            "status": "completed",
                            "recommended_model_count": 3,
                            "recommended_stable_count": 3,
                            "appendix_only_count": 12,
                            "recommended_claim_hygiene_ready": True,
                            "model_claim_scope_csv_path": str(root / "model_claim_scope.csv"),
                            "model_claim_caveat_text": "Main-text model claims are restricted to stable models.",
                        },
                        "transfer_override_seed_stress_test": {
                            "status": "completed",
                            "seed_count": 10,
                            "completed_seed_count": 10,
                            "override_better_transfer_gate_count": 9,
                            "dq3_acceptance_met": True,
                            "per_seed_csv_path": str(root / "seed_stress_per_seed.csv"),
                        },
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
                data_algorithm_quality_review_json_path=quality_json,
            )

            payload = json.loads(Path(summary["summary_json_path"]).read_text(encoding="utf-8"))
            self.assertTrue(payload["data_algorithm_quality_review_present"])
            self.assertEqual(3, payload["data_algorithm_quality_review"]["dataset_count"])
            self.assertEqual(1, payload["data_algorithm_quality_review"]["governance_improved_dataset_count"])
            self.assertTrue(payload["data_algorithm_quality_review"]["dq5_acceptance_met"])
            self.assertTrue(payload["data_algorithm_quality_review"]["manuscript_freeze_packet"]["recommended_claim_hygiene_ready"])
            self.assertTrue(
                payload["data_algorithm_quality_review"]["transfer_override_seed_stress_test"]["dq3_acceptance_met"]
            )
            md_text = Path(summary["summary_md_path"]).read_text(encoding="utf-8")
            self.assertIn("Data-Algorithm Quality-Review Addendum", md_text)
            self.assertIn("DQ-3 acceptance met", md_text)
            self.assertIn("DQ-5 acceptance met", md_text)
            self.assertIn("model-claim hygiene ready", md_text)


if __name__ == "__main__":
    unittest.main()
