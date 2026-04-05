from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.data_algorithm_quality_review import run_data_algorithm_quality_review


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class DataAlgorithmQualityReviewDq5ClosureTest(unittest.TestCase):
    def test_dq5_is_closed_when_claim_hygiene_freeze_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            aggregate_csv = root / "aggregate.csv"
            out_of_time_csv = root / "out_of_time.csv"
            transfer_csv = root / "transfer.csv"
            manuscript_freeze_packet_json = root / "manuscript_freeze_packet.json"
            output_prefix = root / "quality_review"

            _write_csv(
                recommendation_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "f1_mean": 0.82,
                        "f1_std": 0.01,
                        "ece_mean": 0.03,
                    }
                ],
            )
            _write_csv(
                aggregate_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "hgbt",
                        "model_family": "tabular",
                        "f1_mean": 0.82,
                        "f1_std": 0.01,
                        "ece_mean": 0.03,
                        "positive_count_mean": 40,
                    },
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_name": "torch_mlp",
                        "model_family": "regional_raster_cnn",
                        "f1_mean": 0.58,
                        "f1_std": 0.05,
                        "ece_mean": 0.20,
                        "positive_count_mean": 40,
                    },
                ],
            )
            _write_csv(
                out_of_time_csv,
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "delta_f1": -0.02,
                        "baseline_positive_count": 40,
                    }
                ],
            )
            _write_csv(
                transfer_csv,
                [
                    {
                        "source_region": "houston",
                        "target_region": "nola",
                        "delta_f1": 0.03,
                        "target_ece": 0.06,
                    },
                    {
                        "source_region": "houston",
                        "target_region": "seattle",
                        "delta_f1": -0.01,
                        "target_ece": 0.07,
                    },
                ],
            )

            manuscript_freeze_packet_json.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "recommended_model_count": 1,
                        "recommended_stable_count": 1,
                        "appendix_only_count": 1,
                        "recommended_claim_hygiene_ready": True,
                        "model_claim_caveat_text": (
                            "Reviewer caveat: Main-text model claims are restricted to stable candidates."
                        ),
                        "model_claim_scope_csv_path": str(root / "model_claim_scope.csv"),
                    }
                ),
                encoding="utf-8",
            )

            summary = run_data_algorithm_quality_review(
                recommendation_csv_path=recommendation_csv,
                aggregate_csv_path=aggregate_csv,
                out_of_time_csv_path=out_of_time_csv,
                transfer_csv_path=transfer_csv,
                output_prefix=output_prefix,
                manuscript_freeze_packet_json_path=manuscript_freeze_packet_json,
                min_positive_support=30,
                max_ece=0.10,
                max_f1_std=0.03,
                min_out_of_time_delta_f1=-0.05,
                max_negative_transfer_pairs=1,
            )

            self.assertGreaterEqual(int(summary.get("high_risk_model_count", 0)), 1)
            self.assertTrue(bool(summary.get("dq5_acceptance_met")))
            todo_ids = [str(item.get("id", "")) for item in summary.get("todo_items", [])]
            self.assertNotIn("DQ-5", todo_ids)


if __name__ == "__main__":
    unittest.main()
