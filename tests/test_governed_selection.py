from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.governed_selection import build_governed_selection_matrix


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class GovernedSelectionTest(unittest.TestCase):
    def test_build_governed_selection_matrix_applies_gate_and_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            summary_a = root / "outputs" / "noaa_seattle_24h_seed_batch_2026-03-10" / "noaa_seattle_24h_seed_batch_summary.json"
            summary_b = root / "outputs" / "noaa_houston_24h_seed_batch_2026-03-10" / "noaa_houston_24h_seed_batch_summary.json"

            _write_json(
                summary_a,
                {
                    "recommended_model": "logreg",
                    "aggregate_by_model": {
                        "logreg": {"selection_score": 0.70, "calibration_ece_mean": 0.33, "loo_f1_mean_mean": 0.65},
                        "hgbt": {"selection_score": 0.65, "calibration_ece_mean": 0.21, "loo_f1_mean_mean": 0.67},
                        "torch_mlp": {"selection_score": 0.60, "calibration_ece_mean": 0.35, "loo_f1_mean_mean": 0.63},
                    },
                },
            )
            _write_json(
                summary_b,
                {
                    "recommended_model": "hgbt",
                    "aggregate_by_model": {
                        "logreg": {"selection_score": 0.62, "calibration_ece_mean": 0.41, "loo_f1_mean_mean": 0.59},
                        "hgbt": {"selection_score": 0.61, "calibration_ece_mean": 0.37, "loo_f1_mean_mean": 0.58},
                        "torch_mlp": {"selection_score": 0.60, "calibration_ece_mean": 0.39, "loo_f1_mean_mean": 0.57},
                    },
                },
            )

            summary = build_governed_selection_matrix(
                summary_json_paths=[summary_a, summary_b],
                output_prefix=root / "governed_selection",
                candidate_models=["logreg", "hgbt", "torch_mlp"],
                ece_threshold=0.25,
                loo_threshold=0.60,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["source_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["summary_csv_path"]).exists())

            row_map = {row["source"]: row for row in summary["rows"]}
            row_a = row_map[str(summary_a)]
            self.assertEqual("logreg", row_a["plain_recommended"])
            self.assertEqual("hgbt", row_a["governed_recommended"])
            self.assertEqual("best_gate_passed_selection_score", row_a["governed_basis"])

            row_b = row_map[str(summary_b)]
            self.assertEqual("hgbt", row_b["plain_recommended"])
            self.assertEqual("logreg", row_b["governed_recommended"])
            self.assertEqual("fallback_best_selection_score", row_b["governed_basis"])

    def test_governed_selection_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            summary_a = root / "summary_a.json"
            summary_b = root / "summary_b.json"
            _write_json(
                summary_a,
                {
                    "recommended_model": "logreg",
                    "aggregate_by_model": {
                        "logreg": {"selection_score": 0.70, "calibration_ece_mean": 0.33, "loo_f1_mean_mean": 0.65},
                        "hgbt": {"selection_score": 0.65, "calibration_ece_mean": 0.21, "loo_f1_mean_mean": 0.67},
                        "torch_mlp": {"selection_score": 0.60, "calibration_ece_mean": 0.35, "loo_f1_mean_mean": 0.63},
                    },
                },
            )
            _write_json(
                summary_b,
                {
                    "recommended_model": "hgbt",
                    "aggregate_by_model": {
                        "logreg": {"selection_score": 0.62, "calibration_ece_mean": 0.41, "loo_f1_mean_mean": 0.59},
                        "hgbt": {"selection_score": 0.61, "calibration_ece_mean": 0.37, "loo_f1_mean_mean": 0.58},
                        "torch_mlp": {"selection_score": 0.60, "calibration_ece_mean": 0.39, "loo_f1_mean_mean": 0.57},
                    },
                },
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.governed_selection_cli",
                    "--summary-json",
                    str(summary_a),
                    "--summary-json",
                    str(summary_b),
                    "--output-prefix",
                    str(root / "governed_cli"),
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            self.assertTrue((root / "governed_cli_summary.json").exists())
            self.assertTrue((root / "governed_cli_summary.md").exists())
            self.assertTrue((root / "governed_cli_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
