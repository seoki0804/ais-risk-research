from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.study_journal import build_study_journal_from_summary


class StudyJournalTest(unittest.TestCase):
    def test_build_study_journal_from_summary_includes_optional_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            calibration_path = root / "calibration_summary.json"
            calibration_path.write_text(
                json.dumps(
                    {
                        "models": {
                            "rule_score": {"status": "completed", "ece": 0.22},
                            "logreg": {"status": "completed", "ece": 0.11},
                        }
                    }
                ),
                encoding="utf-8",
            )
            loo_path = root / "loo_summary.json"
            loo_path.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "rule_score": {"f1_mean": 0.71},
                            "hgbt": {"f1_mean": 0.80},
                        }
                    }
                ),
                encoding="utf-8",
            )
            case_path = root / "case_summary.json"
            case_path.write_text(
                json.dumps(
                    {
                        "aggregate_models": {
                            "rule_score": {"f1_mean": 0.69, "f1_std": 0.09},
                            "logreg": {"f1_mean": 0.74, "f1_std": 0.05},
                        }
                    }
                ),
                encoding="utf-8",
            )
            study_summary_path = root / "study_summary.json"
            study_summary_path.write_text(
                json.dumps(
                    {
                        "dataset_id": "sample_case",
                        "source_slug": "dma",
                        "start_date": "2026-03-07",
                        "end_date": "2026-03-08",
                        "pairwise_split_strategy": "own_ship",
                        "summary_json_path": str(study_summary_path),
                        "pairwise": {"row_count": 120, "positive_rate": 0.34},
                        "benchmark": {
                            "models": {
                                "rule_score": {"status": "completed", "f1": 0.66},
                                "logreg": {"status": "completed", "f1": 0.78},
                                "hgbt": {"status": "completed", "f1": 0.76},
                            }
                        },
                        "calibration_eval_summary_json_path": str(calibration_path),
                        "own_ship_loo_summary_json_path": str(loo_path),
                        "own_ship_case_eval_summary_json_path": str(case_path),
                    }
                ),
                encoding="utf-8",
            )
            output_path = root / "journal.md"
            written = build_study_journal_from_summary(
                study_summary_path=study_summary_path,
                output_path=output_path,
                author="Tester",
                date_text="2026-03-09",
                topic="sample_case_iteration",
                note="repeat count를 5로 올릴 예정",
            )
            self.assertEqual(str(output_path), written)
            text = output_path.read_text(encoding="utf-8")
            self.assertIn("# 2026-03-09 sample_case_iteration", text)
            self.assertIn("benchmark 최고 F1은 `0.7800`", text)
            self.assertIn("own-ship LOO 기준 best F1 mean은 `0.8000`", text)
            self.assertIn("calibration best ECE는 `0.1100`", text)
            self.assertIn("repeat count를 5로 올릴 예정", text)

    def test_build_study_journal_handles_missing_optional_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            study_summary_path = root / "study_summary.json"
            study_summary_path.write_text(
                json.dumps(
                    {
                        "dataset_id": "sample_case_missing",
                        "pairwise": {"row_count": 10, "positive_rate": 0.2},
                        "benchmark": {"models": {"rule_score": {"status": "completed", "f1": 0.55}}},
                    }
                ),
                encoding="utf-8",
            )
            output_path = root / "journal_missing.md"
            build_study_journal_from_summary(
                study_summary_path=study_summary_path,
                output_path=output_path,
            )
            text = output_path.read_text(encoding="utf-8")
            self.assertIn("sample_case_missing", text)
            self.assertIn("calibration best ECE는 `n/a`", text)
            self.assertIn("own-ship LOO 기준 best F1 mean은 `n/a`", text)


if __name__ == "__main__":
    unittest.main()

