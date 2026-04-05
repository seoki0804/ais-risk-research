from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.multisource_transfer_governance_bridge import run_multisource_transfer_governance_bridge


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class MultiSourceTransferGovernanceBridgeTest(unittest.TestCase):
    def test_builds_governed_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_summary_csv = root / "multisource_source_summary.csv"
            policy_lock_json = root / "policy_lock.json"
            output_prefix = root / "bridge"

            _write_csv(
                source_summary_csv,
                [
                    {
                        "source_region": "houston",
                        "recommended_model": "hgbt",
                        "recommended_combined_pass": "False",
                        "recommended_negative_pair_count": "2",
                        "recommended_max_target_ece": "0.0428",
                    },
                    {
                        "source_region": "nola",
                        "recommended_model": "hgbt",
                        "recommended_combined_pass": "True",
                        "recommended_negative_pair_count": "0",
                        "recommended_max_target_ece": "0.0260",
                    },
                ],
            )
            policy_lock_json.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "source_region_for_transfer_override": "houston",
                        "selected_transfer_model": "rule_score",
                        "selected_transfer_method": "isotonic",
                        "selected_candidate": {"max_target_ece": 0.0684},
                        "governance_ready_for_lock": True,
                        "transfer_policy_pass": True,
                        "out_of_time_policy_pass": True,
                        "baseline_negative_pairs_source": 2,
                        "projected_negative_pairs_source": 0,
                    }
                ),
                encoding="utf-8",
            )

            summary = run_multisource_transfer_governance_bridge(
                multisource_source_summary_csv_path=source_summary_csv,
                transfer_policy_governance_lock_json_path=policy_lock_json,
                output_prefix=output_prefix,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, int(summary["source_count"]))
            self.assertEqual(1, int(summary["baseline_combined_pass_count"]))
            self.assertEqual(2, int(summary["governed_combined_pass_count"]))
            self.assertEqual(1, int(summary["improved_source_count"]))
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["detail_csv_path"]).exists())


if __name__ == "__main__":
    unittest.main()

