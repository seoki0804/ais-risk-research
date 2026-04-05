from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.transfer_calibration_probe import run_transfer_calibration_probe


def _write_predictions(path: Path, model_name: str, labels: list[int], scores: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["timestamp", "own_mmsi", "target_mmsi", "label_future_conflict", f"{model_name}_score", f"{model_name}_pred"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, (label, score) in enumerate(zip(labels, scores)):
            writer.writerow(
                {
                    "timestamp": f"2023-01-01T00:00:{index:02d}Z",
                    "own_mmsi": f"{100000000 + index}",
                    "target_mmsi": f"{200000000 + index}",
                    "label_future_conflict": int(label),
                    f"{model_name}_score": float(score),
                    f"{model_name}_pred": 1 if float(score) >= 0.5 else 0,
                }
            )


class TransferCalibrationProbeTest(unittest.TestCase):
    def test_generates_probe_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            model_name = "hgbt"

            source_val = root / "source_val_predictions.csv"
            source_test = root / "source_test_predictions.csv"
            target = root / "target_predictions.csv"
            _write_predictions(
                source_val,
                model_name=model_name,
                labels=[0, 0, 1, 1, 0, 1],
                scores=[0.20, 0.30, 0.70, 0.80, 0.40, 0.60],
            )
            _write_predictions(
                source_test,
                model_name=model_name,
                labels=[0, 1, 0, 1],
                scores=[0.25, 0.75, 0.35, 0.65],
            )
            _write_predictions(
                target,
                model_name=model_name,
                labels=[0, 1, 0, 1],
                scores=[0.30, 0.60, 0.45, 0.55],
            )

            transfer_summary_json = root / "pair_transfer_summary.json"
            transfer_summary_json.write_text(
                (
                    "{"
                    f"\"source_val_predictions_csv_path\":\"{source_val}\","
                    f"\"source_test_predictions_csv_path\":\"{source_test}\","
                    f"\"target_predictions_csv_path\":\"{target}\""
                    "}"
                ),
                encoding="utf-8",
            )

            detail_csv = root / "transfer_model_scan_detail.csv"
            with detail_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "source_region",
                        "target_region",
                        "model_name",
                        "status",
                        "threshold",
                        "source_f1",
                        "target_f1",
                        "delta_f1",
                        "target_auroc",
                        "target_auprc",
                        "target_ece",
                        "target_brier",
                        "transfer_summary_json_path",
                        "target_predictions_csv_path",
                        "target_calibration_summary_json_path",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "source_region": "houston",
                        "target_region": "nola",
                        "model_name": model_name,
                        "status": "completed",
                        "threshold": "0.50",
                        "source_f1": "1.0",
                        "target_f1": "0.8",
                        "delta_f1": "-0.2",
                        "target_auroc": "0.9",
                        "target_auprc": "0.8",
                        "target_ece": "0.2",
                        "target_brier": "0.1",
                        "transfer_summary_json_path": str(transfer_summary_json),
                        "target_predictions_csv_path": str(target),
                        "target_calibration_summary_json_path": "",
                    }
                )

            summary = run_transfer_calibration_probe(
                transfer_scan_detail_csv_path=detail_csv,
                output_prefix=root / "transfer_calibration_probe",
                source_region_filter="houston",
                model_names=[model_name],
                methods=["none", "platt", "isotonic"],
                threshold_grid_step=0.01,
                ece_gate_max=0.10,
                max_negative_pairs_allowed=1,
                random_seed=42,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(3, int(summary["detail_row_count"]))
            self.assertEqual(3, int(summary["model_method_row_count"]))
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["detail_csv_path"]).exists())
            self.assertTrue(Path(summary["model_method_summary_csv_path"]).exists())


if __name__ == "__main__":
    unittest.main()

