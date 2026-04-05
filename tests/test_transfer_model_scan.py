from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.transfer_model_scan import _parse_targets, run_transfer_model_scan


class TransferModelScanTest(unittest.TestCase):
    def test_parse_targets(self) -> None:
        parsed = _parse_targets("nola:/tmp/nola.csv,seattle:/tmp/sea.csv")
        self.assertEqual([("nola", "/tmp/nola.csv"), ("seattle", "/tmp/sea.csv")], parsed)

    def test_selects_model_from_ece_gated_pool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_input = root / "houston.csv"
            nola_input = root / "nola.csv"
            seattle_input = root / "seattle.csv"
            for path in [source_input, nola_input, seattle_input]:
                path.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            models = ["hgbt", "extra_trees", "torch_mlp"]

            def fake_transfer(**kwargs: object) -> dict[str, object]:
                target = str(kwargs["target_input_path"])
                out_prefix = Path(kwargs["output_prefix"])
                out_prefix.parent.mkdir(parents=True, exist_ok=True)
                target_predictions = out_prefix.with_name(f"{out_prefix.name}_target_predictions.csv")
                with target_predictions.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=["label_future_conflict", "hgbt_score", "extra_trees_score", "torch_mlp_score"],
                    )
                    writer.writeheader()
                    writer.writerow(
                        {
                            "label_future_conflict": "1",
                            "hgbt_score": "0.8",
                            "extra_trees_score": "0.8",
                            "torch_mlp_score": "0.8",
                        }
                    )
                    writer.writerow(
                        {
                            "label_future_conflict": "0",
                            "hgbt_score": "0.2",
                            "extra_trees_score": "0.2",
                            "torch_mlp_score": "0.2",
                        }
                    )
                transfer_json = out_prefix.with_name(f"{out_prefix.name}_transfer_summary.json")
                transfer_json.write_text("{}", encoding="utf-8")

                if target.endswith("nola.csv"):
                    target_f1 = {"hgbt": 0.86, "extra_trees": 0.87, "torch_mlp": 0.83}
                else:
                    target_f1 = {"hgbt": 0.79, "extra_trees": 0.78, "torch_mlp": 0.82}

                return {
                    "models": {
                        model: {
                            "status": "completed",
                            "threshold": 0.4,
                            "source_test": {"f1": 1.0},
                            "target_transfer": {"f1": target_f1[model], "auroc": 0.9, "auprc": 0.8},
                        }
                        for model in models
                    },
                    "transfer_summary_json_path": str(transfer_json),
                    "target_predictions_csv_path": str(target_predictions),
                }

            def fake_calibration(**kwargs: object) -> dict[str, object]:
                path = str(kwargs["predictions_csv_path"])
                if "nola" in path:
                    ece = {"hgbt": 0.03, "extra_trees": 0.03, "torch_mlp": 0.20}
                else:
                    ece = {"hgbt": 0.04, "extra_trees": 0.09, "torch_mlp": 0.23}
                return {
                    "summary_json_path": str(root / "calibration.json"),
                    "models": {
                        model: {
                            "ece": ece[model],
                            "brier_score": 0.03,
                        }
                        for model in models
                    },
                }

            with patch("ais_risk.transfer_model_scan.run_pairwise_transfer_benchmark", side_effect=fake_transfer), patch(
                "ais_risk.transfer_model_scan.run_calibration_evaluation", side_effect=fake_calibration
            ):
                summary = run_transfer_model_scan(
                    source_region="houston",
                    source_input_path=source_input,
                    target_input_paths_by_region={"nola": nola_input, "seattle": seattle_input},
                    model_names=models,
                    output_root=root / "scan_out",
                    calibration_ece_max=0.10,
                )

            self.assertEqual("completed", summary["status"])
            self.assertEqual("hgbt", summary["recommended_model"])
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            rows = list(csv.DictReader(Path(summary["model_summary_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(3, len(rows))


if __name__ == "__main__":
    unittest.main()
