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


class DataAlgorithmQualityReviewDq3ClosureTest(unittest.TestCase):
    def test_dq3_is_closed_when_seed_stress_acceptance_is_met(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            aggregate_csv = root / "aggregate.csv"
            out_of_time_csv = root / "out_of_time.csv"
            transfer_csv = root / "transfer.csv"
            governance_bridge_json = root / "governance_bridge.json"
            governance_bridge_detail_csv = root / "governance_bridge_detail.csv"
            seed_stress_json = root / "seed_stress.json"
            output_prefix = root / "quality_review"

            _write_csv(
                recommendation_csv,
                [{"dataset": "houston_pooled_pairwise", "model_name": "hgbt", "f1_mean": 0.82, "f1_std": 0.0, "ece_mean": 0.02}],
            )
            _write_csv(
                aggregate_csv,
                [{"dataset": "houston_pooled_pairwise", "model_name": "hgbt", "f1_mean": 0.82, "f1_std": 0.0, "ece_mean": 0.02, "positive_count_mean": 40}],
            )
            _write_csv(
                out_of_time_csv,
                [{"dataset": "houston_pooled_pairwise", "delta_f1": -0.02, "baseline_positive_count": 40}],
            )
            _write_csv(
                transfer_csv,
                [
                    {"source_region": "houston", "target_region": "nola", "delta_f1": -0.10, "target_ece": 0.04},
                    {"source_region": "houston", "target_region": "seattle", "delta_f1": -0.20, "target_ece": 0.05},
                ],
            )
            _write_csv(
                governance_bridge_detail_csv,
                [
                    {
                        "source_region": "houston",
                        "governance_mode": "transfer_override_locked",
                        "governed_negative_pairs": 0,
                        "governed_max_target_ece": 0.07,
                    }
                ],
            )
            governance_bridge_json.write_text(
                json.dumps({"detail_csv_path": str(governance_bridge_detail_csv)}),
                encoding="utf-8",
            )
            seed_stress_json.write_text(
                json.dumps({"status": "completed", "dq3_acceptance_met": True}),
                encoding="utf-8",
            )

            summary = run_data_algorithm_quality_review(
                recommendation_csv_path=recommendation_csv,
                aggregate_csv_path=aggregate_csv,
                out_of_time_csv_path=out_of_time_csv,
                transfer_csv_path=transfer_csv,
                output_prefix=output_prefix,
                multisource_transfer_governance_bridge_json_path=governance_bridge_json,
                transfer_override_seed_stress_test_json_path=seed_stress_json,
                min_positive_support=30,
                max_ece=0.10,
                max_f1_std=0.03,
                min_out_of_time_delta_f1=-0.05,
                max_negative_transfer_pairs=1,
            )

            todo_ids = [str(item.get("id", "")) for item in summary.get("todo_items", [])]
            self.assertNotIn("DQ-3", todo_ids)


if __name__ == "__main__":
    unittest.main()

