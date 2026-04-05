from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.batch_review import (
    build_study_batch_review_from_payload,
    build_study_batch_review_from_summary,
)


class BatchReviewTest(unittest.TestCase):
    def test_build_study_batch_review_from_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            validation_summary = outputs / "dataset_x_validation_suite_summary.json"
            validation_summary.write_text(
                json.dumps(
                    {
                        "strategies": {
                            "own_ship_loo": {"best_model": {"name": "logreg", "f1_mean": 0.72}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            error_summary = outputs / "dataset_x_error_summary.json"
            error_summary.write_text(
                json.dumps({"selected_error_row_count": 18, "models": {"logreg": {"fp": 4, "fn": 5}}}),
                encoding="utf-8",
            )
            calibration_summary = outputs / "dataset_x_calibration_summary.json"
            calibration_summary.write_text(
                json.dumps(
                    {
                        "models": {
                            "rule_score": {"status": "completed", "ece": 0.18, "brier_score": 0.21},
                            "logreg": {"status": "completed", "ece": 0.11, "brier_score": 0.19},
                        }
                    }
                ),
                encoding="utf-8",
            )
            own_ship_case_summary = outputs / "dataset_x_own_ship_case_summary.json"
            own_ship_case_summary.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {
                                "ship_count": 3,
                                "f1_mean": 0.71,
                                "f1_std": 0.12,
                                "f1_ci95_width": 0.24,
                                "auroc_mean": 0.78,
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            study_summary = outputs / "dataset_x_study_summary.json"
            study_summary.write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_x",
                        "pairwise": {"row_count": 120, "positive_rate": 0.32},
                        "pairwise_split_strategy": "own_ship",
                        "validation_suite_summary_json_path": str(validation_summary),
                        "error_analysis_summary_json_path": str(error_summary),
                        "calibration_eval_summary_json_path": str(calibration_summary),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case_summary),
                    }
                ),
                encoding="utf-8",
            )

            batch_summary = outputs / "batch_summary.json"
            batch_summary.write_text(
                json.dumps(
                    {
                        "manifest_glob": "data/manifests/*.md",
                        "total_manifests": 1,
                        "completed_count": 1,
                        "failed_count": 0,
                        "items": [
                            {
                                "dataset_id": "dataset_x",
                                "status": "completed",
                                "study_summary_json_path": str(study_summary),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "review.md"
            saved = build_study_batch_review_from_summary(
                batch_summary_path=batch_summary,
                output_path=output,
                review_date="2026-03-09",
            )
            self.assertEqual(str(output), saved)
            text = output.read_text(encoding="utf-8")
            self.assertIn("dataset_x", text)
            self.assertIn("own_ship_loo_f1_mean", text)
            self.assertIn("best_calibration_ece", text)
            self.assertIn("own_ship_case_f1_std", text)
            self.assertIn("own_ship_case_f1_ci95_width", text)
            self.assertIn("alert_level", text)

    def test_build_study_batch_review_from_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output = root / "review_payload.md"
            saved = build_study_batch_review_from_payload(
                batch_summary={
                    "manifest_glob": "data/manifests/*.md",
                    "total_manifests": 0,
                    "completed_count": 0,
                    "failed_count": 0,
                    "items": [],
                },
                output_path=output,
                review_date="2026-03-09",
            )
            self.assertEqual(str(output), saved)
            self.assertTrue(output.exists())

    def test_build_study_batch_review_from_summary_with_previous_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            current_validation = outputs / "current_validation.json"
            current_validation.write_text(
                json.dumps({"strategies": {"own_ship_loo": {"best_model": {"name": "logreg", "f1_mean": 0.70}}}}),
                encoding="utf-8",
            )
            previous_validation = outputs / "previous_validation.json"
            previous_validation.write_text(
                json.dumps({"strategies": {"own_ship_loo": {"best_model": {"name": "logreg", "f1_mean": 0.76}}}}),
                encoding="utf-8",
            )

            current_cal = outputs / "current_cal.json"
            current_cal.write_text(
                json.dumps({"models": {"logreg": {"status": "completed", "ece": 0.24, "brier_score": 0.28}}}),
                encoding="utf-8",
            )
            previous_cal = outputs / "previous_cal.json"
            previous_cal.write_text(
                json.dumps({"models": {"logreg": {"status": "completed", "ece": 0.10, "brier_score": 0.18}}}),
                encoding="utf-8",
            )

            current_case = outputs / "current_case.json"
            current_case.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {
                                "ship_count": 3,
                                "f1_mean": 0.68,
                                "f1_std": 0.16,
                                "f1_ci95_width": 0.26,
                                "auroc_mean": 0.76,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            previous_case = outputs / "previous_case.json"
            previous_case.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {
                                "ship_count": 3,
                                "f1_mean": 0.72,
                                "f1_std": 0.08,
                                "f1_ci95_width": 0.18,
                                "auroc_mean": 0.79,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            current_study = outputs / "dataset_y_current_study_summary.json"
            current_study.write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_y",
                        "pairwise": {"row_count": 200, "positive_rate": 0.4},
                        "pairwise_split_strategy": "own_ship",
                        "validation_suite_summary_json_path": str(current_validation),
                        "calibration_eval_summary_json_path": str(current_cal),
                        "own_ship_case_eval_summary_json_path": str(current_case),
                    }
                ),
                encoding="utf-8",
            )
            previous_study = outputs / "dataset_y_previous_study_summary.json"
            previous_study.write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_y",
                        "pairwise": {"row_count": 210, "positive_rate": 0.38},
                        "pairwise_split_strategy": "own_ship",
                        "validation_suite_summary_json_path": str(previous_validation),
                        "calibration_eval_summary_json_path": str(previous_cal),
                        "own_ship_case_eval_summary_json_path": str(previous_case),
                    }
                ),
                encoding="utf-8",
            )

            current_batch = outputs / "current_batch_summary.json"
            current_batch.write_text(
                json.dumps(
                    {
                        "manifest_glob": "data/manifests/*.md",
                        "total_manifests": 1,
                        "completed_count": 1,
                        "failed_count": 0,
                        "items": [{"dataset_id": "dataset_y", "status": "completed", "study_summary_json_path": str(current_study)}],
                    }
                ),
                encoding="utf-8",
            )
            previous_batch = outputs / "previous_batch_summary.json"
            previous_batch.write_text(
                json.dumps(
                    {
                        "manifest_glob": "data/manifests/*.md",
                        "total_manifests": 1,
                        "completed_count": 1,
                        "failed_count": 0,
                        "items": [{"dataset_id": "dataset_y", "status": "completed", "study_summary_json_path": str(previous_study)}],
                    }
                ),
                encoding="utf-8",
            )

            output = root / "review_with_delta.md"
            saved = build_study_batch_review_from_summary(
                batch_summary_path=current_batch,
                previous_batch_summary_path=previous_batch,
                output_path=output,
                review_date="2026-03-09",
            )
            self.assertEqual(str(output), saved)
            text = output.read_text(encoding="utf-8")
            self.assertIn("High Alert 우선 대상", text)
            self.assertIn("delta_alert_count", text)
            self.assertIn("delta_case_ci95_width", text)
            self.assertIn("dataset_y", text)

    def test_build_study_batch_review_uses_own_ship_loo_summary_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)

            own_ship_loo_summary = outputs / "dataset_z_own_ship_loo_summary.json"
            own_ship_loo_summary.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {"f1_mean": 0.73},
                            "rule_score": {"f1_mean": 0.61},
                        }
                    }
                ),
                encoding="utf-8",
            )
            own_ship_case_summary = outputs / "dataset_z_own_ship_case_summary.json"
            own_ship_case_summary.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "logreg": {
                                "ship_count": 1,
                                "f1_mean": 0.80,
                                "f1_std": 0.05,
                                "f1_ci95_width": 0.10,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            study_summary = outputs / "dataset_z_study_summary.json"
            study_summary.write_text(
                json.dumps(
                    {
                        "dataset_id": "dataset_z",
                        "pairwise": {"row_count": 120, "positive_rate": 0.21},
                        "pairwise_split_strategy": "own_ship",
                        "own_ship_loo_summary_json_path": str(own_ship_loo_summary),
                        "own_ship_case_eval_summary_json_path": str(own_ship_case_summary),
                    }
                ),
                encoding="utf-8",
            )
            batch_summary = outputs / "batch_summary.json"
            batch_summary.write_text(
                json.dumps(
                    {
                        "manifest_glob": "data/manifests/*.md",
                        "total_manifests": 1,
                        "completed_count": 1,
                        "failed_count": 0,
                        "items": [
                            {
                                "dataset_id": "dataset_z",
                                "status": "completed",
                                "study_summary_json_path": str(study_summary),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "review_fallback.md"
            saved = build_study_batch_review_from_summary(
                batch_summary_path=batch_summary,
                output_path=output,
                review_date="2026-03-09",
            )
            self.assertEqual(str(output), saved)
            text = output.read_text(encoding="utf-8")
            self.assertIn("dataset_z", text)
            self.assertIn("| dataset_z | 120 |", text)
            self.assertIn("| 0.7300 |", text)


if __name__ == "__main__":
    unittest.main()
