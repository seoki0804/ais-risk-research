from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.transfer_override_seed_stress_test import run_transfer_override_seed_stress_test


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TransferOverrideSeedStressTest(unittest.TestCase):
    def test_generates_stress_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_dir = root / "input"
            output_prefix = root / "stress_summary"
            _write_csv(input_dir / "houston_pooled_pairwise.csv", [{"x": 1}])
            _write_csv(input_dir / "nola_pooled_pairwise.csv", [{"x": 1}])
            _write_csv(input_dir / "seattle_pooled_pairwise.csv", [{"x": 1}])

            def fake_transfer_model_scan(**kwargs: object) -> dict[str, object]:
                out_root = Path(str(kwargs["output_root"]))
                detail_csv = out_root / "houston_transfer_model_scan_detail.csv"
                _write_csv(
                    detail_csv,
                    [
                        {
                            "source_region": "houston",
                            "target_region": "nola",
                            "model_name": "hgbt",
                            "status": "completed",
                        }
                    ],
                )
                return {"detail_csv_path": str(detail_csv)}

            def fake_transfer_calibration_probe(**kwargs: object) -> dict[str, object]:
                out_prefix = Path(str(kwargs["output_prefix"]))
                seed_value = int(out_prefix.parent.name.replace("seed_", ""))
                summary_csv = out_prefix.with_name(f"{out_prefix.name}_model_method_summary.csv")
                detail_csv = out_prefix.with_name(f"{out_prefix.name}_detail.csv")

                baseline_neg = 2 if seed_value in {41, 43} else 1
                override_neg = 0
                _write_csv(
                    summary_csv,
                    [
                        {
                            "source_region": "houston",
                            "model_name": "hgbt",
                            "method": "none",
                            "pair_count": 2,
                            "negative_fixed_count": baseline_neg,
                            "max_target_ece": 0.04,
                            "combined_pass_fixed": seed_value == 42,
                            "mean_delta_f1_fixed": -0.18,
                        },
                        {
                            "source_region": "houston",
                            "model_name": "rule_score",
                            "method": "isotonic",
                            "pair_count": 2,
                            "negative_fixed_count": override_neg,
                            "max_target_ece": 0.07,
                            "combined_pass_fixed": True,
                            "mean_delta_f1_fixed": 0.55,
                        },
                    ],
                )
                _write_csv(
                    detail_csv,
                    [
                        {
                            "source_region": "houston",
                            "target_region": "nola",
                            "model_name": "hgbt",
                            "method": "none",
                            "status": "completed",
                            "source_f1_fixed": 1.0,
                            "target_f1_fixed": 0.85,
                        },
                        {
                            "source_region": "houston",
                            "target_region": "seattle",
                            "model_name": "hgbt",
                            "method": "none",
                            "status": "completed",
                            "source_f1_fixed": 1.0,
                            "target_f1_fixed": 0.80,
                        },
                        {
                            "source_region": "houston",
                            "target_region": "nola",
                            "model_name": "rule_score",
                            "method": "isotonic",
                            "status": "completed",
                            "source_f1_fixed": 0.10,
                            "target_f1_fixed": 0.95,
                        },
                        {
                            "source_region": "houston",
                            "target_region": "seattle",
                            "model_name": "rule_score",
                            "method": "isotonic",
                            "status": "completed",
                            "source_f1_fixed": 0.10,
                            "target_f1_fixed": 0.90,
                        },
                    ],
                )
                return {
                    "detail_csv_path": str(detail_csv),
                    "model_method_summary_csv_path": str(summary_csv),
                }

            with patch(
                "ais_risk.transfer_override_seed_stress_test.run_transfer_model_scan",
                side_effect=fake_transfer_model_scan,
            ), patch(
                "ais_risk.transfer_override_seed_stress_test.run_transfer_calibration_probe",
                side_effect=fake_transfer_calibration_probe,
            ):
                summary = run_transfer_override_seed_stress_test(
                    input_dir=input_dir,
                    output_prefix=output_prefix,
                    source_region="houston",
                    target_regions=["nola", "seattle"],
                    baseline_model="hgbt",
                    override_model="rule_score",
                    override_method="isotonic",
                    random_seeds="41,42,43",
                )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(3, int(summary["seed_count"]))
            self.assertEqual(3, int(summary["completed_seed_count"]))
            self.assertEqual(1, int(summary["baseline_combined_pass_fixed_count"]))
            self.assertEqual(3, int(summary["override_combined_pass_fixed_count"]))
            self.assertEqual(3, int(summary["override_better_transfer_gate_count"]))
            self.assertTrue(bool(summary["dq3_acceptance_met"]))
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["per_seed_csv_path"]).exists())


if __name__ == "__main__":
    unittest.main()

