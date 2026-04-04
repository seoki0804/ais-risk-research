from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.all_models_seed_sweep import run_all_models_seed_sweep


class AllModelsSeedSweepTest(unittest.TestCase):
    def test_seed_sweep_aggregates_rows_and_winners(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "houston_pooled_pairwise.csv"
            input_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            def fake_run_all_supported_models(input_path: str | Path, output_dir: str | Path, random_seed: int, **_: object) -> dict[str, object]:
                run_dir = Path(output_dir)
                run_dir.mkdir(parents=True, exist_ok=True)
                leaderboard_path = run_dir / "leaderboard.csv"
                f1_hgbt = 0.80 if int(random_seed) == 41 else 0.70
                f1_cnn = 0.75 if int(random_seed) == 41 else 0.85
                rows = [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "status": "completed",
                        "f1": f1_hgbt,
                        "precision": 0.8,
                        "recall": 0.8,
                        "auroc": 0.9,
                        "auprc": 0.85,
                        "accuracy": 0.88,
                        "threshold": 0.5,
                        "sample_count": 100,
                        "positive_count": 20,
                        "negative_count": 80,
                        "tp": 16,
                        "fp": 4,
                        "tn": 76,
                        "fn": 4,
                        "ece": 0.05,
                        "brier_score": 0.08,
                        "elapsed_seconds": 0.1,
                        "device": "",
                        "epochs": "",
                        "hidden_dim": "",
                        "split_strategy": "own_ship",
                        "summary_json_path": str(run_dir / "summary.json"),
                        "predictions_csv_path": str(run_dir / "pred.csv"),
                        "notes": "",
                    },
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "regional_raster_cnn",
                        "model_name": "cnn_focal",
                        "status": "completed",
                        "f1": f1_cnn,
                        "precision": 0.75,
                        "recall": 0.85,
                        "auroc": 0.92,
                        "auprc": 0.86,
                        "accuracy": 0.89,
                        "threshold": 0.7,
                        "sample_count": 100,
                        "positive_count": 20,
                        "negative_count": 80,
                        "tp": 17,
                        "fp": 6,
                        "tn": 74,
                        "fn": 3,
                        "ece": 0.08,
                        "brier_score": 0.09,
                        "elapsed_seconds": 0.2,
                        "device": "mps",
                        "epochs": 20,
                        "hidden_dim": "",
                        "split_strategy": "own_ship",
                        "summary_json_path": str(run_dir / "summary.json"),
                        "predictions_csv_path": str(run_dir / "pred.csv"),
                        "notes": "loss=focal",
                    },
                ]
                with leaderboard_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
                return {
                    "summary_json_path": str(run_dir / "summary.json"),
                    "leaderboard_csv_path": str(leaderboard_path),
                    "split_was_auto_adjusted": True,
                    "effective_train_fraction": 0.5,
                    "effective_val_fraction": 0.2,
                }

            with patch("ais_risk.all_models_seed_sweep.run_all_supported_models", side_effect=fake_run_all_supported_models):
                summary = run_all_models_seed_sweep(
                    input_paths_by_region={"houston": input_csv},
                    output_root=root / "out",
                    seeds=[41, 42],
                    include_regional_cnn=True,
                )

            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["aggregate_csv_path"]).exists())
            self.assertTrue(Path(summary["winner_summary_csv_path"]).exists())
            self.assertTrue(Path(summary["recommendation_csv_path"]).exists())
            self.assertTrue(Path(summary["recommendation_json_path"]).exists())
            self.assertTrue(Path(summary["recommendation_md_path"]).exists())

            aggregate_rows = list(csv.DictReader(Path(summary["aggregate_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(2, len(aggregate_rows))
            hgbt = [row for row in aggregate_rows if row["model_name"] == "hgbt"][0]
            cnn = [row for row in aggregate_rows if row["model_name"] == "cnn_focal"][0]
            self.assertEqual("2", hgbt["runs"])
            self.assertEqual("2", cnn["runs"])
            self.assertAlmostEqual(0.75, float(hgbt["f1_mean"]), places=6)
            self.assertAlmostEqual(0.80, float(cnn["f1_mean"]), places=6)
            self.assertIn("f1_ci95", hgbt)
            self.assertIn("auroc_ci95", hgbt)
            self.assertIn("ece_ci95", hgbt)
            self.assertGreaterEqual(float(hgbt["f1_ci95"]), 0.0)

            winner_rows = list(csv.DictReader(Path(summary["winner_summary_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(2, len(winner_rows))
            win_map = {row["model_name"]: int(row["wins"]) for row in winner_rows}
            self.assertEqual(1, win_map["hgbt"])
            self.assertEqual(1, win_map["cnn_focal"])

            recommendation_rows = list(csv.DictReader(Path(summary["recommendation_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(1, len(recommendation_rows))
            self.assertEqual("cnn_focal", recommendation_rows[0]["model_name"])
            self.assertEqual("pass_within_f1_band", recommendation_rows[0]["gate_status"])

    def test_seed_sweep_recommendation_relaxes_when_no_model_passes_ece_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_csv = root / "houston_pooled_pairwise.csv"
            input_csv.write_text("timestamp,own_mmsi,target_mmsi,label_future_conflict\n", encoding="utf-8")

            def fake_run_all_supported_models(input_path: str | Path, output_dir: str | Path, random_seed: int, **_: object) -> dict[str, object]:
                run_dir = Path(output_dir)
                run_dir.mkdir(parents=True, exist_ok=True)
                leaderboard_path = run_dir / "leaderboard.csv"
                rows = [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "status": "completed",
                        "f1": 0.79,
                        "precision": 0.8,
                        "recall": 0.8,
                        "auroc": 0.9,
                        "auprc": 0.85,
                        "accuracy": 0.88,
                        "threshold": 0.5,
                        "sample_count": 100,
                        "positive_count": 20,
                        "negative_count": 80,
                        "tp": 16,
                        "fp": 4,
                        "tn": 76,
                        "fn": 4,
                        "ece": 0.20,
                        "brier_score": 0.08,
                        "elapsed_seconds": 0.1,
                        "device": "",
                        "epochs": "",
                        "hidden_dim": "",
                        "split_strategy": "own_ship",
                        "summary_json_path": str(run_dir / "summary.json"),
                        "predictions_csv_path": str(run_dir / "pred.csv"),
                        "notes": "",
                    },
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "regional_raster_cnn",
                        "model_name": "cnn_focal",
                        "status": "completed",
                        "f1": 0.80,
                        "precision": 0.75,
                        "recall": 0.85,
                        "auroc": 0.92,
                        "auprc": 0.86,
                        "accuracy": 0.89,
                        "threshold": 0.7,
                        "sample_count": 100,
                        "positive_count": 20,
                        "negative_count": 80,
                        "tp": 17,
                        "fp": 6,
                        "tn": 74,
                        "fn": 3,
                        "ece": 0.30,
                        "brier_score": 0.09,
                        "elapsed_seconds": 0.2,
                        "device": "mps",
                        "epochs": 20,
                        "hidden_dim": "",
                        "split_strategy": "own_ship",
                        "summary_json_path": str(run_dir / "summary.json"),
                        "predictions_csv_path": str(run_dir / "pred.csv"),
                        "notes": "loss=focal",
                    },
                ]
                with leaderboard_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
                return {
                    "summary_json_path": str(run_dir / "summary.json"),
                    "leaderboard_csv_path": str(leaderboard_path),
                    "split_was_auto_adjusted": False,
                    "effective_train_fraction": 0.6,
                    "effective_val_fraction": 0.2,
                }

            with patch("ais_risk.all_models_seed_sweep.run_all_supported_models", side_effect=fake_run_all_supported_models):
                summary = run_all_models_seed_sweep(
                    input_paths_by_region={"houston": input_csv},
                    output_root=root / "out",
                    seeds=[41, 42],
                    include_regional_cnn=True,
                    recommendation_max_ece_mean=0.10,
                )

            recommendation_rows = list(csv.DictReader(Path(summary["recommendation_csv_path"]).open("r", encoding="utf-8", newline="")))
            self.assertEqual(1, len(recommendation_rows))
            self.assertEqual("hgbt", recommendation_rows[0]["model_name"])
            self.assertEqual("no_gate_pass_candidate", recommendation_rows[0]["gate_status"])


if __name__ == "__main__":
    unittest.main()
