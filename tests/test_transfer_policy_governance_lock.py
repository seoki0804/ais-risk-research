from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.transfer_policy_governance_lock import run_transfer_policy_governance_lock


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TransferPolicyGovernanceLockTest(unittest.TestCase):
    def test_generates_governance_lock_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_csv = root / "recommendation.csv"
            transfer_csv = root / "transfer_check.csv"
            oot_policy_json = root / "out_of_time_policy.json"
            calibration_detail_csv = root / "calibration_detail.csv"

            _write_csv(
                recommendation_csv,
                [
                    {"dataset": "houston_pooled_pairwise", "model_name": "hgbt"},
                    {"dataset": "nola_pooled_pairwise", "model_name": "hgbt"},
                ],
            )
            _write_csv(
                transfer_csv,
                [
                    {
                        "source_region": "houston",
                        "target_region": "nola",
                        "source_dataset": "houston_pooled_pairwise",
                        "target_dataset": "nola_pooled_pairwise",
                        "recommended_model": "hgbt",
                        "status": "completed",
                        "source_f1": 1.0,
                        "target_f1": 0.80,
                        "delta_f1": -0.20,
                        "source_auroc": 1.0,
                        "target_auroc": 0.9,
                        "delta_auroc": -0.1,
                        "target_ece": 0.03,
                        "target_brier": 0.04,
                        "threshold": 0.4,
                        "transfer_summary_json_path": str(root / "old_transfer_summary.json"),
                        "target_predictions_csv_path": "",
                        "target_calibration_summary_json_path": "",
                        "notes": "",
                    },
                    {
                        "source_region": "nola",
                        "target_region": "houston",
                        "source_dataset": "nola_pooled_pairwise",
                        "target_dataset": "houston_pooled_pairwise",
                        "recommended_model": "hgbt",
                        "status": "completed",
                        "source_f1": 0.40,
                        "target_f1": 0.70,
                        "delta_f1": 0.30,
                        "source_auroc": 0.9,
                        "target_auroc": 0.9,
                        "delta_auroc": 0.0,
                        "target_ece": 0.02,
                        "target_brier": 0.03,
                        "threshold": 0.2,
                        "transfer_summary_json_path": str(root / "nola_transfer_summary.json"),
                        "target_predictions_csv_path": "",
                        "target_calibration_summary_json_path": "",
                        "notes": "",
                    },
                ],
            )
            oot_policy_json.write_text(
                json.dumps(
                    {
                        "houston_rows": [
                            {
                                "region": "houston",
                                "dataset": "houston_pooled_pairwise",
                                "policy": "fixed_baseline_threshold",
                                "status": "completed",
                                "delta_f1": -0.03,
                                "out_of_time_ece": 0.02,
                                "combined_pass": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            _write_csv(
                calibration_detail_csv,
                [
                    {
                        "source_region": "houston",
                        "target_region": "nola",
                        "model_name": "rule_score",
                        "method": "isotonic",
                        "status": "completed",
                        "threshold": 0.4,
                        "source_f1_fixed": 0.1,
                        "target_f1_fixed": 0.72,
                        "delta_f1_fixed": 0.62,
                        "target_best_threshold": 0.35,
                        "target_best_f1": 0.74,
                        "target_retune_gain_f1": 0.02,
                        "delta_f1_retuned": 0.64,
                        "target_ece": 0.05,
                        "target_brier": 0.08,
                        "transfer_summary_json_path": str(root / "new_transfer_summary.json"),
                    }
                ],
            )

            summary = run_transfer_policy_governance_lock(
                recommendation_csv_path=recommendation_csv,
                transfer_check_csv_path=transfer_csv,
                out_of_time_threshold_policy_compare_json_path=oot_policy_json,
                transfer_calibration_probe_detail_csv_path=calibration_detail_csv,
                output_prefix=root / "governance_lock",
                source_region_for_transfer_override="houston",
                metric_mode="fixed",
                max_target_ece=0.10,
                max_negative_pairs_allowed=1,
                required_out_of_time_policy="fixed_baseline_threshold",
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual("rule_score", summary["selected_transfer_model"])
            self.assertEqual("isotonic", summary["selected_transfer_method"])
            self.assertEqual(1, int(summary["baseline_negative_pairs_global"]))
            self.assertEqual(0, int(summary["projected_negative_pairs_global"]))
            self.assertTrue(bool(summary["governance_ready_for_lock"]))
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["policy_lock_csv_path"]).exists())
            self.assertTrue(Path(summary["projected_transfer_check_csv_path"]).exists())
            self.assertTrue(Path(summary["candidate_summary_csv_path"]).exists())

            projected_rows = list(csv.DictReader(Path(summary["projected_transfer_check_csv_path"]).open("r", encoding="utf-8")))
            houston_rows = [row for row in projected_rows if row["source_region"] == "houston"]
            self.assertEqual(1, len(houston_rows))
            self.assertEqual("rule_score/isotonic", houston_rows[0]["recommended_model"])
            self.assertGreater(float(houston_rows[0]["delta_f1"]), 0.0)


if __name__ == "__main__":
    unittest.main()
