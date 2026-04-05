from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.validation_leaderboard import build_validation_leaderboard


class ValidationLeaderboardTest(unittest.TestCase):
    def test_build_validation_leaderboard_from_study_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation_a = outputs / "dataset_a_validation_suite_summary.json"
            validation_b = outputs / "dataset_b_validation_suite_summary.json"
            calibration_a = outputs / "dataset_a_calibration_eval_summary.json"
            calibration_b = outputs / "dataset_b_calibration_eval_summary.json"
            own_ship_case_a = outputs / "dataset_a_own_ship_case_eval_summary.json"
            own_ship_case_b = outputs / "dataset_b_own_ship_case_eval_summary.json"
            validation_a.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.71, "auroc": 0.8, "auprc": 0.75}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "hgbt", "f1": 0.65, "auroc": 0.7, "auprc": 0.68}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.66, "auroc_mean": 0.72, "auprc_mean": 0.7}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            calibration_a.write_text(
                json.dumps(
                    {
                        "models": {
                            "rule_score": {"status": "completed", "ece": 0.17, "brier_score": 0.22},
                            "logreg": {"status": "completed", "ece": 0.11, "brier_score": 0.18},
                            "hgbt": {"status": "completed", "ece": 0.09, "brier_score": 0.17},
                        }
                    }
                ),
                encoding="utf-8",
            )
            validation_b.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.81, "auroc": 0.85, "auprc": 0.82}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.76, "auroc": 0.8, "auprc": 0.77}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.74, "auroc_mean": 0.79, "auprc_mean": 0.78}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            calibration_b.write_text(
                json.dumps(
                    {
                        "models": {
                            "rule_score": {"status": "completed", "ece": 0.14, "brier_score": 0.20},
                            "logreg": {"status": "completed", "ece": 0.07, "brier_score": 0.16},
                            "hgbt": {"status": "completed", "ece": 0.10, "brier_score": 0.19},
                        }
                    }
                ),
                encoding="utf-8",
            )
            own_ship_case_a.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {"ship_count": 3, "f1_mean": 0.63, "f1_std": 0.04, "auroc_mean": 0.72},
                            "hgbt": {"ship_count": 3, "f1_mean": 0.66, "f1_std": 0.03, "auroc_mean": 0.75},
                        }
                    }
                ),
                encoding="utf-8",
            )
            own_ship_case_b.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {"ship_count": 4, "f1_mean": 0.70, "f1_std": 0.02, "auroc_mean": 0.79},
                            "hgbt": {"ship_count": 4, "f1_mean": 0.68, "f1_std": 0.03, "auroc_mean": 0.76},
                        }
                    }
                ),
                encoding="utf-8",
            )

            study_a = outputs / "dataset_a_study_summary.json"
            study_b = outputs / "dataset_b_study_summary.json"
            study_a.write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_a",
                        "manifest_path": "data/manifests/dataset_a.md",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation_a),
                        "calibration_eval_summary_json_path": str(calibration_a),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case_a),
                    }
                ),
                encoding="utf-8",
            )
            study_b.write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_b",
                        "manifest_path": "data/manifests/dataset_b.md",
                        "pairwise": {"row_count": 120, "positive_rate": 0.4},
                        "validation_suite_summary_json_path": str(validation_b),
                        "calibration_eval_summary_json_path": str(calibration_b),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case_b),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="own_ship_loo_f1_mean",
                descending=True,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["row_count"])
            self.assertTrue(Path(summary["output_csv_path"]).exists())
            self.assertTrue(Path(summary["output_md_path"]).exists())
            md_text = Path(summary["output_md_path"]).read_text(encoding="utf-8")
            self.assertIn("dataset_b", md_text)
            self.assertIn("dataset_a", md_text)
            self.assertIn("Best Calibration ECE", md_text)
            self.assertIn("Alert Level", md_text)
            csv_text = Path(summary["output_csv_path"]).read_text(encoding="utf-8")
            self.assertIn("calibration_best_ece", csv_text)
            self.assertIn("own_ship_case_f1_mean", csv_text)
            self.assertIn("own_ship_case_f1_ci95_width", csv_text)
            self.assertIn("alert_own_ship_case_ci95_wide", csv_text)
            self.assertIn("alert_level", csv_text)

    def test_leaderboard_deduplicates_same_dataset_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation_low = outputs / "dataset_x_low_validation_suite_summary.json"
            validation_high = outputs / "dataset_x_high_validation_suite_summary.json"
            calibration_low = outputs / "dataset_x_low_calibration_eval_summary.json"
            calibration_high = outputs / "dataset_x_high_calibration_eval_summary.json"
            own_ship_case_low = outputs / "dataset_x_low_own_ship_case_eval_summary.json"
            own_ship_case_high = outputs / "dataset_x_high_own_ship_case_eval_summary.json"
            validation_low.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.60, "auroc": 0.7, "auprc": 0.62}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.58, "auroc": 0.68, "auprc": 0.6}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.55, "auroc_mean": 0.66, "auprc_mean": 0.57}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            calibration_low.write_text(
                json.dumps(
                    {
                        "models": {
                            "logreg": {"status": "completed", "ece": 0.19, "brier_score": 0.25},
                        }
                    }
                ),
                encoding="utf-8",
            )
            validation_high.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.75, "auroc": 0.82, "auprc": 0.77}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.73, "auroc": 0.8, "auprc": 0.75}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.71, "auroc_mean": 0.79, "auprc_mean": 0.74}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            calibration_high.write_text(
                json.dumps(
                    {
                        "models": {
                            "logreg": {"status": "completed", "ece": 0.08, "brier_score": 0.16},
                        }
                    }
                ),
                encoding="utf-8",
            )
            own_ship_case_low.write_text(
                json.dumps({"aggregate_models": {"logreg": {"ship_count": 2, "f1_mean": 0.52, "f1_std": 0.08, "auroc_mean": 0.64}}}),
                encoding="utf-8",
            )
            own_ship_case_high.write_text(
                json.dumps({"aggregate_models": {"logreg": {"ship_count": 2, "f1_mean": 0.69, "f1_std": 0.03, "auroc_mean": 0.77}}}),
                encoding="utf-8",
            )

            study_low = outputs / "dataset_x_low_study_summary.json"
            study_high = outputs / "dataset_x_high_study_summary.json"
            study_low.write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_x",
                        "manifest_path": "data/manifests/dataset_x.md",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation_low),
                        "calibration_eval_summary_json_path": str(calibration_low),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case_low),
                    }
                ),
                encoding="utf-8",
            )
            study_high.write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_x",
                        "manifest_path": "data/manifests/dataset_x.md",
                        "pairwise": {"row_count": 110, "positive_rate": 0.35},
                        "validation_suite_summary_json_path": str(validation_high),
                        "calibration_eval_summary_json_path": str(calibration_high),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case_high),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="own_ship_loo_f1_mean",
                descending=True,
                deduplicate_dataset_id=True,
            )
            self.assertEqual(1, summary["row_count"])
            csv_text = Path(summary["output_csv_path"]).read_text(encoding="utf-8")
            self.assertIn("0.71", csv_text)

    def test_leaderboard_can_sort_by_calibration_ece_ascending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation_a = outputs / "dataset_a_validation_suite_summary.json"
            validation_b = outputs / "dataset_b_validation_suite_summary.json"
            calibration_a = outputs / "dataset_a_calibration_eval_summary.json"
            calibration_b = outputs / "dataset_b_calibration_eval_summary.json"
            validation_a.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.70, "auroc": 0.8, "auprc": 0.73}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.68, "auroc": 0.77, "auprc": 0.71}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.66, "auroc_mean": 0.75, "auprc_mean": 0.69}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            validation_b.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "hgbt", "f1": 0.69, "auroc": 0.79, "auprc": 0.72}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "hgbt", "f1": 0.67, "auroc": 0.76, "auprc": 0.7}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "hgbt", "f1_mean": 0.65, "auroc_mean": 0.74, "auprc_mean": 0.68}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            calibration_a.write_text(
                json.dumps({"models": {"logreg": {"status": "completed", "ece": 0.12, "brier_score": 0.20}}}),
                encoding="utf-8",
            )
            calibration_b.write_text(
                json.dumps({"models": {"hgbt": {"status": "completed", "ece": 0.05, "brier_score": 0.15}}}),
                encoding="utf-8",
            )

            (outputs / "dataset_a_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_a",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation_a),
                        "calibration_eval_summary_json_path": str(calibration_a),
                    }
                ),
                encoding="utf-8",
            )
            (outputs / "dataset_b_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_b",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation_b),
                        "calibration_eval_summary_json_path": str(calibration_b),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="calibration_best_ece",
                descending=False,
            )
            self.assertEqual("completed", summary["status"])
            md_text = Path(summary["output_md_path"]).read_text(encoding="utf-8")
            first_data_line = [line for line in md_text.splitlines() if line.startswith("| 1 |")][0]
            self.assertIn("dataset_b", first_data_line)

    def test_leaderboard_can_sort_by_own_ship_case_f1_mean(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation = outputs / "validation_suite_summary.json"
            validation.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.60, "auroc": 0.7, "auprc": 0.62}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.58, "auroc": 0.68, "auprc": 0.6}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.57, "auroc_mean": 0.67, "auprc_mean": 0.59}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            case_a = outputs / "dataset_a_own_ship_case_eval_summary.json"
            case_b = outputs / "dataset_b_own_ship_case_eval_summary.json"
            case_a.write_text(
                json.dumps({"aggregate_models": {"logreg": {"ship_count": 3, "f1_mean": 0.61, "f1_std": 0.05, "auroc_mean": 0.71}}}),
                encoding="utf-8",
            )
            case_b.write_text(
                json.dumps({"aggregate_models": {"logreg": {"ship_count": 3, "f1_mean": 0.74, "f1_std": 0.04, "auroc_mean": 0.82}}}),
                encoding="utf-8",
            )

            (outputs / "dataset_a_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_a",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation),
                        "own_ship_case_eval_summary_json_path": str(case_a),
                    }
                ),
                encoding="utf-8",
            )
            (outputs / "dataset_b_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_b",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation),
                        "own_ship_case_eval_summary_json_path": str(case_b),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="own_ship_case_f1_mean",
                descending=True,
            )
            self.assertEqual("completed", summary["status"])
            md_text = Path(summary["output_md_path"]).read_text(encoding="utf-8")
            first_data_line = [line for line in md_text.splitlines() if line.startswith("| 1 |")][0]
            self.assertIn("dataset_b", first_data_line)

    def test_leaderboard_deduplicate_respects_ascending_calibration_sort(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation = outputs / "validation_suite_summary.json"
            validation.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.61, "auroc": 0.72, "auprc": 0.63}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.59, "auroc": 0.69, "auprc": 0.61}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.58, "auroc_mean": 0.68, "auprc_mean": 0.60}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            calibration_high = outputs / "dataset_x_high_calibration_eval_summary.json"
            calibration_low = outputs / "dataset_x_low_calibration_eval_summary.json"
            calibration_high.write_text(
                json.dumps({"models": {"logreg": {"status": "completed", "ece": 0.18, "brier_score": 0.24}}}),
                encoding="utf-8",
            )
            calibration_low.write_text(
                json.dumps({"models": {"logreg": {"status": "completed", "ece": 0.06, "brier_score": 0.15}}}),
                encoding="utf-8",
            )

            (outputs / "dataset_x_a_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_x",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation),
                        "calibration_eval_summary_json_path": str(calibration_high),
                    }
                ),
                encoding="utf-8",
            )
            (outputs / "dataset_x_b_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_x",
                        "pairwise": {"row_count": 110, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation),
                        "calibration_eval_summary_json_path": str(calibration_low),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="calibration_best_ece",
                descending=False,
                deduplicate_dataset_id=True,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, summary["row_count"])
            csv_text = Path(summary["output_csv_path"]).read_text(encoding="utf-8")
            self.assertIn("0.06", csv_text)

    def test_leaderboard_generates_alert_level_from_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation = outputs / "validation_suite_summary.json"
            calibration = outputs / "calibration_eval_summary.json"
            own_ship_case = outputs / "own_ship_case_eval_summary.json"
            validation.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.64, "auroc": 0.74, "auprc": 0.66}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.63, "auroc": 0.73, "auprc": 0.65}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.62, "auroc_mean": 0.72, "auprc_mean": 0.64}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            calibration.write_text(
                json.dumps({"models": {"logreg": {"status": "completed", "ece": 0.22, "brier_score": 0.27}}}),
                encoding="utf-8",
            )
            own_ship_case.write_text(
                json.dumps({"aggregate_models": {"logreg": {"ship_count": 3, "f1_mean": 0.61, "f1_std": 0.16, "auroc_mean": 0.70}}}),
                encoding="utf-8",
            )
            (outputs / "dataset_alert_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_alert",
                        "pairwise": {"row_count": 120, "positive_rate": 0.4},
                        "validation_suite_summary_json_path": str(validation),
                        "calibration_eval_summary_json_path": str(calibration),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="own_ship_loo_f1_mean",
                descending=True,
                own_ship_case_f1_std_threshold=0.10,
                calibration_best_ece_threshold=0.15,
            )
            self.assertEqual("completed", summary["status"])
            import csv

            with Path(summary["output_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(1, len(rows))
            self.assertEqual("high", rows[0]["alert_level"])
            self.assertEqual("2", rows[0]["alert_count"])

    def test_leaderboard_can_alert_on_case_ci95_width(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation = outputs / "validation_suite_summary.json"
            own_ship_case = outputs / "own_ship_case_eval_summary.json"
            validation.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.64, "auroc": 0.74, "auprc": 0.66}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.63, "auroc": 0.73, "auprc": 0.65}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.62, "auroc_mean": 0.72, "auprc_mean": 0.64}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            own_ship_case.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {
                                "ship_count": 4,
                                "f1_mean": 0.61,
                                "f1_std": 0.05,
                                "f1_ci95_low": 0.45,
                                "f1_ci95_high": 0.77,
                                "f1_ci95_width": 0.32,
                                "f1_std_repeat_mean": 0.11,
                                "auroc_mean": 0.70,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (outputs / "dataset_alert_ci_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_alert_ci",
                        "pairwise": {"row_count": 120, "positive_rate": 0.4},
                        "validation_suite_summary_json_path": str(validation),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="own_ship_loo_f1_mean",
                descending=True,
                own_ship_case_f1_std_threshold=0.10,
                calibration_best_ece_threshold=-1.0,
                own_ship_case_f1_ci95_width_threshold=0.20,
            )
            self.assertEqual("completed", summary["status"])
            import csv

            with Path(summary["output_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(1, len(rows))
            self.assertEqual("True", rows[0]["alert_own_ship_case_ci95_wide"])
            self.assertEqual("medium", rows[0]["alert_level"])
            self.assertEqual("1", rows[0]["alert_count"])

    def test_leaderboard_includes_rows_without_validation_suite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            own_ship_loo = outputs / "dataset_no_validation_own_ship_loo_summary.json"
            own_ship_case = outputs / "dataset_no_validation_own_ship_case_eval_summary.json"
            calibration = outputs / "dataset_no_validation_calibration_eval_summary.json"
            own_ship_loo.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {"f1_mean": 0.62, "auroc_mean": 0.71, "auprc_mean": 0.64},
                        }
                    }
                ),
                encoding="utf-8",
            )
            own_ship_case.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {
                                "ship_count": 1,
                                "f1_mean": 0.70,
                                "f1_std": 0.04,
                                "f1_ci95_width": 0.08,
                                "f1_std_repeat_mean": 0.03,
                                "f1_std_repeat_max": 0.05,
                                "auroc_mean": 0.78,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            calibration.write_text(
                json.dumps({"models": {"logreg": {"status": "completed", "ece": 0.09, "brier_score": 0.17}}}),
                encoding="utf-8",
            )
            (outputs / "dataset_no_validation_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_no_validation",
                        "pairwise": {"row_count": 90, "positive_rate": 0.28},
                        "pairwise_split_strategy": "own_ship",
                        "own_ship_loo_summary_json_path": str(own_ship_loo),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case),
                        "calibration_eval_summary_json_path": str(calibration),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="own_ship_case_f1_std_repeat_mean",
                descending=False,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(1, summary["row_count"])
            csv_text = Path(summary["output_csv_path"]).read_text(encoding="utf-8")
            self.assertIn("dataset_no_validation", csv_text)
            self.assertIn("0.03", csv_text)

    def test_leaderboard_can_sort_by_own_ship_case_f1_std_repeat_mean(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation = outputs / "validation_suite_summary.json"
            validation.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "timestamp_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.64, "auroc": 0.74, "auprc": 0.66}},
                            "own_ship_split": {"status": "completed", "best_model": {"name": "logreg", "f1": 0.63, "auroc": 0.73, "auprc": 0.65}},
                            "own_ship_loo": {"status": "completed", "best_model": {"name": "logreg", "f1_mean": 0.62, "auroc_mean": 0.72, "auprc_mean": 0.64}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            case_a = outputs / "dataset_a_own_ship_case_eval_summary.json"
            case_b = outputs / "dataset_b_own_ship_case_eval_summary.json"
            case_a.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {"ship_count": 3, "f1_mean": 0.71, "f1_std": 0.05, "f1_std_repeat_mean": 0.08}
                        }
                    }
                ),
                encoding="utf-8",
            )
            case_b.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {"ship_count": 3, "f1_mean": 0.69, "f1_std": 0.04, "f1_std_repeat_mean": 0.02}
                        }
                    }
                ),
                encoding="utf-8",
            )

            (outputs / "dataset_a_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_a",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation),
                        "own_ship_case_eval_summary_json_path": str(case_a),
                    }
                ),
                encoding="utf-8",
            )
            (outputs / "dataset_b_study_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_b",
                        "pairwise": {"row_count": 100, "positive_rate": 0.3},
                        "validation_suite_summary_json_path": str(validation),
                        "own_ship_case_eval_summary_json_path": str(case_b),
                    }
                ),
                encoding="utf-8",
            )

            summary = build_validation_leaderboard(
                study_summary_glob=str(outputs / "*_study_summary.json"),
                output_csv_path=outputs / "leaderboard.csv",
                output_md_path=outputs / "leaderboard.md",
                sort_by="own_ship_case_f1_std_repeat_mean",
                descending=False,
            )
            self.assertEqual("completed", summary["status"])
            md_text = Path(summary["output_md_path"]).read_text(encoding="utf-8")
            first_data_line = [line for line in md_text.splitlines() if line.startswith("| 1 |")][0]
            self.assertIn("dataset_b", first_data_line)


if __name__ == "__main__":
    unittest.main()
