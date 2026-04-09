from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.manuscript_enhancement_pack import run_manuscript_enhancement_pack


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class ManuscriptEnhancementPackTest(unittest.TestCase):
    def test_builds_draft_and_figures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            results = root / "results"
            output = root / "manuscript"

            _write_csv(
                results / "all_models_multiarea_leaderboard.csv",
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "status": "completed",
                        "f1": 0.82,
                        "ece": 0.02,
                        "auroc": 0.98,
                    },
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "regional_raster_cnn",
                        "model_name": "cnn_focal",
                        "status": "completed",
                        "f1": 0.81,
                        "ece": 0.14,
                        "auroc": 0.99,
                    },
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "status": "completed",
                        "f1": 0.60,
                        "ece": 0.03,
                        "auroc": 0.97,
                    },
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_family": "regional_raster_cnn",
                        "model_name": "cnn_weighted",
                        "status": "completed",
                        "f1": 0.44,
                        "ece": 0.10,
                        "auroc": 0.96,
                    },
                ],
            )
            _write_csv(
                results / "all_models_seed_sweep_recommendation.csv",
                [
                    {
                        "dataset": "houston_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "f1_mean": 0.82,
                        "ece_mean": 0.02,
                        "selection_rule": "ece_gate_then_max_f1",
                    },
                    {
                        "dataset": "nola_pooled_pairwise",
                        "model_family": "tabular",
                        "model_name": "hgbt",
                        "f1_mean": 0.60,
                        "ece_mean": 0.03,
                        "selection_rule": "ece_gate_then_max_f1",
                    },
                ],
            )
            _write_csv(
                results / "transfer_recommendation_check.csv",
                [
                    {
                        "source_region": "houston",
                        "target_region": "nola",
                        "recommended_model": "hgbt",
                        "delta_f1": -0.10,
                        "target_ece": 0.04,
                        "target_auroc": 0.98,
                    },
                    {
                        "source_region": "nola",
                        "target_region": "houston",
                        "recommended_model": "hgbt",
                        "delta_f1": 0.30,
                        "target_ece": 0.02,
                        "target_auroc": 0.97,
                    },
                ],
            )
            _write_csv(
                results / "external_validity_manuscript_assets_2026-04-05_10seed_scenario_panels.csv",
                [
                    {
                        "region": "houston",
                        "model_name": "hgbt",
                        "f1_mean": 0.82,
                        "ece": 0.02,
                        "fp": 1,
                        "fn": 11,
                        "reliability_figure_path": "/tmp/houston_rel.png",
                        "heatmap_contour_figure_svg_path": "/tmp/houston_map.svg",
                        "calibration_note": "well calibrated",
                        "error_note": "FN pressure",
                    }
                ],
            )

            summary = run_manuscript_enhancement_pack(
                results_root=results,
                output_root=output,
            )

            expected_keys = {
                "recommended_summary_csv_path",
                "family_summary_csv_path",
                "transfer_summary_csv_path",
                "transfer_uncertainty_summary_csv_path",
                "ablation_tabular_vs_cnn_csv_path",
                "figure_1_model_family_comparison_svg_path",
                "figure_2_transfer_delta_f1_heatmap_svg_path",
                "figure_3_pipeline_overview_svg_path",
                "figure_index_md_path",
                "manuscript_draft_ko_md_path",
                "manuscript_draft_en_md_path",
                "manuscript_draft_md_path",
                "manuscript_todo_md_path",
                "terminology_mapping_md_path",
                "figure_captions_bilingual_md_path",
                "submission_template_tex_path",
                "consistency_report_md_path",
                "prior_work_evidence_matrix_md_path",
                "examiner_critical_todo_md_path",
            }
            self.assertEqual(expected_keys, set(summary.keys()))

            for key, value in summary.items():
                self.assertTrue(Path(value).exists(), msg=f"Missing output for {key}: {value}")

            todo_text = Path(summary["manuscript_todo_md_path"]).read_text(encoding="utf-8")
            self.assertIn("## B. Scientific Strengthening", todo_text)
            self.assertIn("- [x] Expand Methods section", todo_text)
            self.assertIn("- [x] Add explicit uncertainty/confidence interval sentences", todo_text)
            self.assertIn("- [x] Add ablation-focused paragraph", todo_text)
            self.assertIn("## C. Submission Readiness", todo_text)
            self.assertIn("- [x] Transform markdown draft to target venue template", todo_text)
            self.assertIn("- [x] Final consistency pass between tables, figures, and manuscript claims", todo_text)
            self.assertIn("## D. Reviewer-Critical Upgrades (Next Iteration)", todo_text)

            prior_work_text = Path(summary["prior_work_evidence_matrix_md_path"]).read_text(encoding="utf-8")
            self.assertIn("RW-01", prior_work_text)
            self.assertIn("RW-13", prior_work_text)
            self.assertIn("Crossref", prior_work_text)

            examiner_text = Path(summary["examiner_critical_todo_md_path"]).read_text(encoding="utf-8")
            self.assertIn("Critical Findings", examiner_text)
            self.assertIn("Detailed TODO with Acceptance Criteria", examiner_text)


if __name__ == "__main__":
    unittest.main()
