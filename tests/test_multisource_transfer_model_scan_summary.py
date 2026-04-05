from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.multisource_transfer_model_scan_summary import run_multisource_transfer_model_scan_summary


class MultiSourceTransferModelScanSummaryTest(unittest.TestCase):
    def test_builds_summary_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scan_root = root / "scan"
            scan_root.mkdir(parents=True, exist_ok=True)

            for source_region, recommended_model in [("alpha", "m1"), ("beta", "m2")]:
                summary_json = scan_root / f"{source_region}_transfer_model_scan.json"
                summary_json.write_text(
                    json.dumps(
                        {
                            "status": "completed",
                            "source_region": source_region,
                            "recommended_model": recommended_model,
                        }
                    ),
                    encoding="utf-8",
                )

            with (scan_root / "alpha_transfer_model_scan_detail.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "source_region",
                        "target_region",
                        "model_name",
                        "status",
                        "delta_f1",
                        "target_ece",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "source_region": "alpha",
                            "target_region": "beta",
                            "model_name": "m1",
                            "status": "completed",
                            "delta_f1": "-0.10",
                            "target_ece": "0.03",
                        },
                        {
                            "source_region": "alpha",
                            "target_region": "gamma",
                            "model_name": "m1",
                            "status": "completed",
                            "delta_f1": "0.02",
                            "target_ece": "0.04",
                        },
                        {
                            "source_region": "alpha",
                            "target_region": "beta",
                            "model_name": "m2",
                            "status": "completed",
                            "delta_f1": "0.05",
                            "target_ece": "0.02",
                        },
                        {
                            "source_region": "alpha",
                            "target_region": "gamma",
                            "model_name": "m2",
                            "status": "completed",
                            "delta_f1": "0.04",
                            "target_ece": "0.03",
                        },
                    ]
                )

            with (scan_root / "beta_transfer_model_scan_detail.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "source_region",
                        "target_region",
                        "model_name",
                        "status",
                        "delta_f1",
                        "target_ece",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "source_region": "beta",
                            "target_region": "alpha",
                            "model_name": "m1",
                            "status": "completed",
                            "delta_f1": "0.02",
                            "target_ece": "0.05",
                        },
                        {
                            "source_region": "beta",
                            "target_region": "gamma",
                            "model_name": "m1",
                            "status": "completed",
                            "delta_f1": "0.01",
                            "target_ece": "0.06",
                        },
                        {
                            "source_region": "beta",
                            "target_region": "alpha",
                            "model_name": "m2",
                            "status": "completed",
                            "delta_f1": "0.03",
                            "target_ece": "0.11",
                        },
                        {
                            "source_region": "beta",
                            "target_region": "gamma",
                            "model_name": "m2",
                            "status": "completed",
                            "delta_f1": "0.03",
                            "target_ece": "0.12",
                        },
                    ]
                )

            summary = run_multisource_transfer_model_scan_summary(
                scan_output_root=scan_root,
                source_regions=["alpha", "beta"],
                output_prefix=root / "multisource_summary",
                max_target_ece=0.10,
                max_negative_pairs_allowed=1,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, int(summary["source_count"]))
            self.assertEqual(2, int(summary["recommendation_mismatch_count"]))
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["detail_csv_path"]).exists())
            self.assertTrue(Path(summary["source_summary_csv_path"]).exists())


if __name__ == "__main__":
    unittest.main()
