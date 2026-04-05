from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.workflow import run_ingestion_workflow


class WorkflowTest(unittest.TestCase):
    def test_run_ingestion_workflow_creates_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run_ingestion_workflow(
                input_path="examples/sample_ais.csv",
                output_dir=temp_dir,
                project_config_path="configs/base.toml",
                ingestion_config_path="configs/ingestion/marinecadastre_harbor.toml",
                top_n=2,
                min_targets=1,
            )

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["resolved_ingestion"]["bundle_name"], "marinecadastre_harbor")
            self.assertGreaterEqual(summary["recommendation_count"], 1)
            self.assertTrue(Path(summary["schema_probe_path"]).exists())
            self.assertTrue(Path(summary["curated_csv_path"]).exists())
            self.assertTrue(Path(summary["tracks_csv_path"]).exists())
            self.assertTrue(Path(summary["own_ship_candidates_path"]).exists())
            self.assertTrue(Path(summary["demo_package_manifest_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())

            manifest = json.loads(Path(summary["demo_package_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["case_count"], 2)
            self.assertTrue(Path(summary["demo_package_master_report_path"]).exists())
            self.assertTrue(Path(summary["demo_package_figure_bundle_manifest_path"]).exists())
            self.assertTrue(Path(summary["demo_package_figure_bundle_html_path"]).exists())
            self.assertTrue(Path(summary["demo_package_figure_bundle_md_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_assets_manifest_path"]).exists())
            self.assertTrue(Path(summary["demo_package_artifact_catalog_path"]).exists())
            self.assertTrue(Path(summary["demo_package_artifact_catalog_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_audience_guide_path"]).exists())
            self.assertTrue(Path(summary["demo_package_audience_guide_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_handoff_checklist_path"]).exists())
            self.assertTrue(Path(summary["demo_package_handoff_checklist_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_deliverable_readiness_path"]).exists())
            self.assertTrue(Path(summary["demo_package_deliverable_readiness_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_case_table_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_scenario_table_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_ablation_table_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_claim_matrix_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_claim_matrix_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_reviewer_faq_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_reviewer_faq_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_presentation_outline_path"]).exists())
            self.assertTrue(Path(summary["demo_package_presentation_outline_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_demo_talk_track_path"]).exists())
            self.assertTrue(Path(summary["demo_package_demo_talk_track_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_defense_packet_path"]).exists())
            self.assertTrue(Path(summary["demo_package_defense_packet_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_portfolio_case_study_path"]).exists())
            self.assertTrue(Path(summary["demo_package_portfolio_case_study_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_interview_answer_bank_path"]).exists())
            self.assertTrue(Path(summary["demo_package_interview_answer_bank_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_advisor_review_pack_path"]).exists())
            self.assertTrue(Path(summary["demo_package_reviewer_pack_path"]).exists())
            self.assertTrue(Path(summary["demo_package_interview_pack_path"]).exists())
            self.assertTrue(Path(summary["demo_package_portfolio_pack_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_case_latex_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_scenario_latex_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_ablation_latex_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_captions_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_captions_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_summary_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_summary_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_full_draft_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_full_draft_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_full_draft_tex_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_results_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_results_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_results_tex_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_methods_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_methods_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_methods_tex_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_discussion_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_discussion_ko_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_discussion_tex_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_appendix_md_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_appendix_ko_md_path"]).exists())
            self.assertTrue(Path(summary["demo_package_paper_appendix_tex_path"]).exists())


if __name__ == "__main__":
    unittest.main()
