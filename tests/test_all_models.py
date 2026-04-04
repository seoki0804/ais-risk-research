from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.all_models import ALL_TABULAR_MODEL_NAMES, run_all_supported_models


class AllModelsTest(unittest.TestCase):
    def test_run_all_supported_models_builds_leaderboard_with_tabular_and_cnn(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "pairwise.csv"
            input_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            def fake_benchmark(**_: object) -> dict[str, object]:
                pred_path = root / "tabular_predictions.csv"
                with pred_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=[
                            "label_future_conflict",
                            "rule_score_pred",
                            "logreg_pred",
                            "hgbt_pred",
                            "random_forest_pred",
                            "extra_trees_pred",
                            "torch_mlp_pred",
                        ],
                    )
                    writer.writeheader()
                    writer.writerow(
                        {
                            "label_future_conflict": "1",
                            "rule_score_pred": "1",
                            "logreg_pred": "1",
                            "hgbt_pred": "1",
                            "random_forest_pred": "1",
                            "extra_trees_pred": "1",
                            "torch_mlp_pred": "1",
                        }
                    )
                    writer.writerow(
                        {
                            "label_future_conflict": "0",
                            "rule_score_pred": "0",
                            "logreg_pred": "0",
                            "hgbt_pred": "0",
                            "random_forest_pred": "0",
                            "extra_trees_pred": "0",
                            "torch_mlp_pred": "0",
                        }
                    )
                return {
                    "summary_json_path": str(root / "tabular_summary.json"),
                    "predictions_csv_path": str(pred_path),
                    "models": {
                        "rule_score": {"f1": 0.50, "auroc": 0.60, "auprc": 0.55, "precision": 0.51, "recall": 0.49, "accuracy": 0.58, "threshold": 0.5, "elapsed_seconds": 0.01},
                        "logreg": {"f1": 0.70, "auroc": 0.80, "auprc": 0.71, "precision": 0.69, "recall": 0.72, "accuracy": 0.75, "threshold": 0.5, "elapsed_seconds": 0.02},
                        "hgbt": {"f1": 0.82, "auroc": 0.90, "auprc": 0.84, "precision": 0.81, "recall": 0.84, "accuracy": 0.86, "threshold": 0.45, "elapsed_seconds": 0.03},
                        "random_forest": {
                            "f1": 0.79,
                            "auroc": 0.88,
                            "auprc": 0.82,
                            "precision": 0.78,
                            "recall": 0.80,
                            "accuracy": 0.84,
                            "threshold": 0.50,
                            "elapsed_seconds": 0.05,
                        },
                        "extra_trees": {
                            "f1": 0.80,
                            "auroc": 0.89,
                            "auprc": 0.83,
                            "precision": 0.79,
                            "recall": 0.81,
                            "accuracy": 0.85,
                            "threshold": 0.50,
                            "elapsed_seconds": 0.06,
                        },
                        "torch_mlp": {
                            "f1": 0.77,
                            "auroc": 0.85,
                            "auprc": 0.79,
                            "precision": 0.76,
                            "recall": 0.78,
                            "accuracy": 0.80,
                            "threshold": 0.5,
                            "elapsed_seconds": 0.04,
                            "device": "mps",
                            "epochs": 40,
                            "hidden_dim": 64,
                        },
                    },
                }

            def fake_calibration(**_: object) -> dict[str, object]:
                return {
                    "summary_json_path": str(root / "tabular_calibration_summary.json"),
                    "models": {
                        "rule_score": {"ece": 0.10, "brier_score": 0.20},
                        "logreg": {"ece": 0.08, "brier_score": 0.15},
                        "hgbt": {"ece": 0.04, "brier_score": 0.10},
                        "random_forest": {"ece": 0.07, "brier_score": 0.13},
                        "extra_trees": {"ece": 0.06, "brier_score": 0.12},
                        "torch_mlp": {"ece": 0.12, "brier_score": 0.18},
                    },
                }

            def fake_cnn(output_prefix: str | Path, loss_type: str, **_: object) -> dict[str, object]:
                pred_path = Path(output_prefix).with_name(f"{Path(output_prefix).name}_predictions.csv")
                with pred_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=["label_future_conflict", "cnn_pred", "cnn_temp_pred"])
                    writer.writeheader()
                    writer.writerow({"label_future_conflict": "1", "cnn_pred": "1", "cnn_temp_pred": "1"})
                    writer.writerow({"label_future_conflict": "0", "cnn_pred": "0", "cnn_temp_pred": "0"})
                return {
                    "summary_json_path": str(Path(output_prefix).with_name(f"{Path(output_prefix).name}_summary.json")),
                    "predictions_csv_path": str(pred_path),
                    "metrics": {
                        "status": "completed",
                        "f1": 0.66 if loss_type == "weighted_bce" else 0.64,
                        "auroc": 0.77,
                        "auprc": 0.69,
                        "precision": 0.63,
                        "recall": 0.70,
                        "accuracy": 0.72,
                        "threshold": 0.5,
                        "elapsed_seconds": 1.2,
                    },
                    "temperature_scaling": {
                        "metrics": {
                            "status": "completed",
                            "f1": 0.68 if loss_type == "weighted_bce" else 0.65,
                            "auroc": 0.77,
                            "auprc": 0.69,
                            "precision": 0.65,
                            "recall": 0.71,
                            "accuracy": 0.73,
                            "threshold": 0.5,
                        }
                    },
                    "calibration_metrics": {"ece": 0.09, "brier_score": 0.16},
                    "temperature_scaled_calibration_metrics": {"ece": 0.06, "brier_score": 0.14},
                    "training_info": {"device": "mps", "epochs": 10},
                }

            with patch("ais_risk.all_models.run_pairwise_benchmark", side_effect=fake_benchmark), patch(
                "ais_risk.all_models.run_calibration_evaluation", side_effect=fake_calibration
            ), patch("ais_risk.all_models.run_regional_raster_cnn_benchmark", side_effect=fake_cnn):
                summary = run_all_supported_models(
                    input_path=input_csv,
                    output_dir=root / "out",
                    include_regional_cnn=True,
                    cnn_losses=["weighted_bce", "focal"],
                )

            leaderboard_csv = Path(summary["leaderboard_csv_path"])
            self.assertTrue(leaderboard_csv.exists())
            rows = list(csv.DictReader(leaderboard_csv.open("r", encoding="utf-8", newline="")))
            self.assertEqual(len(ALL_TABULAR_MODEL_NAMES) + 4, len(rows))
            model_names = {row["model_name"] for row in rows}
            self.assertIn("hgbt", model_names)
            self.assertIn("random_forest", model_names)
            self.assertIn("extra_trees", model_names)
            self.assertIn("torch_mlp", model_names)
            self.assertIn("cnn_weighted", model_names)
            self.assertIn("cnn_weighted_temp", model_names)
            self.assertIn("cnn_focal", model_names)
            self.assertIn("cnn_focal_temp", model_names)
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["leaderboard_md_path"]).exists())

    def test_run_all_supported_models_marks_torch_mlp_skipped_without_torch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "pairwise.csv"
            input_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            def fake_benchmark(model_names: list[str], **_: object) -> dict[str, object]:
                self.assertEqual([model_name for model_name in ALL_TABULAR_MODEL_NAMES if model_name != "torch_mlp"], model_names)
                pred_path = root / "tabular_predictions.csv"
                with pred_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=[
                            "label_future_conflict",
                            "rule_score_pred",
                            "logreg_pred",
                            "hgbt_pred",
                            "random_forest_pred",
                            "extra_trees_pred",
                        ],
                    )
                    writer.writeheader()
                    writer.writerow(
                        {
                            "label_future_conflict": "1",
                            "rule_score_pred": "1",
                            "logreg_pred": "1",
                            "hgbt_pred": "1",
                            "random_forest_pred": "1",
                            "extra_trees_pred": "1",
                        }
                    )
                    writer.writerow(
                        {
                            "label_future_conflict": "0",
                            "rule_score_pred": "0",
                            "logreg_pred": "0",
                            "hgbt_pred": "0",
                            "random_forest_pred": "0",
                            "extra_trees_pred": "0",
                        }
                    )
                return {
                    "summary_json_path": str(root / "tabular_summary.json"),
                    "predictions_csv_path": str(pred_path),
                    "models": {
                        "rule_score": {"f1": 0.50},
                        "logreg": {"f1": 0.70},
                        "hgbt": {"f1": 0.82},
                        "random_forest": {"f1": 0.79},
                        "extra_trees": {"f1": 0.80},
                    },
                }

            def fake_calibration(**_: object) -> dict[str, object]:
                return {"summary_json_path": str(root / "tabular_calibration_summary.json"), "models": {}}

            with patch("ais_risk.all_models.benchmark_module.torch", None), patch(
                "ais_risk.all_models.run_pairwise_benchmark", side_effect=fake_benchmark
            ), patch("ais_risk.all_models.run_calibration_evaluation", side_effect=fake_calibration):
                summary = run_all_supported_models(input_path=input_csv, output_dir=root / "out")

            rows = list(csv.DictReader(Path(summary["leaderboard_csv_path"]).open("r", encoding="utf-8", newline="")))
            torch_rows = [row for row in rows if row["model_name"] == "torch_mlp"]
            self.assertEqual(1, len(torch_rows))
            self.assertEqual("skipped", torch_rows[0]["status"])
            self.assertIn("PyTorch is not installed.", torch_rows[0]["notes"])

    def test_run_all_supported_models_can_auto_adjust_split_fractions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "pairwise.csv"
            input_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            pred_path = root / "tabular_predictions.csv"
            with pred_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "label_future_conflict",
                        "rule_score_pred",
                        "logreg_pred",
                        "hgbt_pred",
                        "random_forest_pred",
                        "extra_trees_pred",
                        "torch_mlp_pred",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "label_future_conflict": "1",
                        "rule_score_pred": "1",
                        "logreg_pred": "1",
                        "hgbt_pred": "1",
                        "random_forest_pred": "1",
                        "extra_trees_pred": "1",
                        "torch_mlp_pred": "1",
                    }
                )
                writer.writerow(
                    {
                        "label_future_conflict": "0",
                        "rule_score_pred": "0",
                        "logreg_pred": "0",
                        "hgbt_pred": "0",
                        "random_forest_pred": "0",
                        "extra_trees_pred": "0",
                        "torch_mlp_pred": "0",
                    }
                )

            def fake_benchmark(**kwargs: object) -> dict[str, object]:
                self.assertEqual(0.5, kwargs["train_fraction"])
                self.assertEqual(0.2, kwargs["val_fraction"])
                return {
                    "summary_json_path": str(root / "tabular_summary.json"),
                    "predictions_csv_path": str(pred_path),
                    "models": {
                        "rule_score": {"f1": 0.50},
                        "logreg": {"f1": 0.70},
                        "hgbt": {"f1": 0.82},
                        "random_forest": {"f1": 0.79},
                        "extra_trees": {"f1": 0.80},
                        "torch_mlp": {"f1": 0.77},
                    },
                }

            def fake_calibration(**_: object) -> dict[str, object]:
                return {"summary_json_path": str(root / "tabular_calibration_summary.json"), "models": {}}

            with patch("ais_risk.all_models.benchmark_module.load_pairwise_dataset_rows", return_value=[]), patch(
                "ais_risk.all_models._choose_support_aware_split", return_value=(0.5, 0.2, [{"positive_count": 12}], True)
            ), patch("ais_risk.all_models.run_pairwise_benchmark", side_effect=fake_benchmark), patch(
                "ais_risk.all_models.run_calibration_evaluation", side_effect=fake_calibration
            ):
                summary = run_all_supported_models(
                    input_path=input_csv,
                    output_dir=root / "out",
                    auto_adjust_split_for_support=True,
                    include_regional_cnn=False,
                )

            self.assertTrue(summary["split_was_auto_adjusted"])
            self.assertEqual(0.5, summary["effective_train_fraction"])
            self.assertEqual(0.2, summary["effective_val_fraction"])


if __name__ == "__main__":
    unittest.main()
