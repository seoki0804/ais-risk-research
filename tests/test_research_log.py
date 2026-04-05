from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.research_log import build_benchmark_research_log


class ResearchLogTest(unittest.TestCase):
    def test_benchmark_research_log_is_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            benchmark_summary_path = tmp_path / "benchmark_summary.json"
            pairwise_stats_path = tmp_path / "pairwise_stats.json"
            output_path = tmp_path / "research_log.md"

            benchmark_summary_path.write_text(
                json.dumps(
                    {
                        "input_path": "outputs/sample_pairwise_dataset.csv",
                        "row_count": 84,
                        "positive_rate": 0.5,
                        "split": {
                            "train_rows": 48,
                            "val_rows": 12,
                            "test_rows": 24,
                        },
                        "models": {
                            "rule_score": {
                                "threshold": 0.10,
                                "auroc": 0.6,
                                "auprc": 0.5,
                                "f1": 0.5,
                                "precision": 0.5,
                                "recall": 0.5,
                            },
                            "logreg": {
                                "threshold": 0.20,
                                "auroc": 0.9,
                                "auprc": 0.8,
                                "f1": 0.7,
                                "precision": 0.8,
                                "recall": 0.6,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            pairwise_stats_path.write_text(
                json.dumps(
                    {
                        "dataset_path": "outputs/sample_pairwise_dataset.csv",
                        "future_min_distance_summary": {
                            "min_nm": 0.8,
                            "median_nm": 1.6,
                            "max_nm": 3.1,
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = build_benchmark_research_log(
                benchmark_summary_path=benchmark_summary_path,
                pairwise_stats_path=pairwise_stats_path,
                output_path=output_path,
                date_text="2026-03-07",
            )

            self.assertEqual(str(output_path), result)
            text = output_path.read_text(encoding="utf-8")
            self.assertIn("best model", text)
            self.assertIn("logreg", text)
            self.assertIn("future separation", text)


if __name__ == "__main__":
    unittest.main()
