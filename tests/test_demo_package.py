from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.config import load_config
from ais_risk.csv_tools import preprocess_ais_csv
from ais_risk.demo_package import build_recommended_demo_package_from_csv
from ais_risk.trajectory import reconstruct_trajectory_csv


class DemoPackageTest(unittest.TestCase):
    def test_demo_package_builds_case_directories_and_index(self) -> None:
        root = Path(__file__).resolve().parents[1]
        input_path = root / "examples" / "sample_ais.csv"
        config_path = root / "configs" / "base.toml"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            tracks_path = Path(temp_dir) / "tracks.csv"
            output_dir = Path(temp_dir) / "demo"
            preprocess_ais_csv(input_path, curated_path)
            reconstruct_trajectory_csv(curated_path, tracks_path)
            manifest = build_recommended_demo_package_from_csv(
                input_path=tracks_path,
                config=load_config(config_path),
                output_dir=output_dir,
                radius_nm=6.0,
                top_n=2,
            )

            self.assertEqual(manifest["case_count"], 2)
            manifest_payload = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest_payload["cases"]), 2)
            self.assertTrue((output_dir / "index.html").exists())
            self.assertTrue((output_dir / "summary.md").exists())
            self.assertTrue((output_dir / "master_report.html").exists())
            self.assertTrue((output_dir / "master_findings.md").exists())
            self.assertTrue((output_dir / "package_experiment_aggregate.json").exists())
            self.assertTrue((output_dir / "package_ablation_aggregate.json").exists())
            self.assertTrue((output_dir / "figure_bundle.html").exists())
            self.assertTrue((output_dir / "figure_bundle.md").exists())
            self.assertTrue((output_dir / "figure_bundle_manifest.json").exists())
            self.assertTrue((output_dir / "artifact_catalog.md").exists())
            self.assertTrue((output_dir / "artifact_catalog_ko.md").exists())
            self.assertTrue((output_dir / "audience_guide.md").exists())
            self.assertTrue((output_dir / "audience_guide_ko.md").exists())
            self.assertTrue((output_dir / "handoff_checklist.md").exists())
            self.assertTrue((output_dir / "handoff_checklist_ko.md").exists())
            self.assertTrue((output_dir / "deliverable_readiness.md").exists())
            self.assertTrue((output_dir / "deliverable_readiness_ko.md").exists())
            self.assertTrue((output_dir / "paper_case_table.csv").exists())
            self.assertTrue((output_dir / "paper_scenario_table.csv").exists())
            self.assertTrue((output_dir / "paper_ablation_current_table.csv").exists())
            self.assertTrue((output_dir / "paper_claim_matrix.csv").exists())
            self.assertTrue((output_dir / "paper_claim_matrix.md").exists())
            self.assertTrue((output_dir / "paper_claim_matrix_ko.md").exists())
            self.assertTrue((output_dir / "paper_reviewer_faq.md").exists())
            self.assertTrue((output_dir / "paper_reviewer_faq_ko.md").exists())
            self.assertTrue((output_dir / "presentation_outline.md").exists())
            self.assertTrue((output_dir / "presentation_outline_ko.md").exists())
            self.assertTrue((output_dir / "demo_talk_track.md").exists())
            self.assertTrue((output_dir / "demo_talk_track_ko.md").exists())
            self.assertTrue((output_dir / "defense_packet.md").exists())
            self.assertTrue((output_dir / "defense_packet_ko.md").exists())
            self.assertTrue((output_dir / "portfolio_case_study.md").exists())
            self.assertTrue((output_dir / "portfolio_case_study_ko.md").exists())
            self.assertTrue((output_dir / "interview_answer_bank.md").exists())
            self.assertTrue((output_dir / "interview_answer_bank_ko.md").exists())
            self.assertTrue((output_dir / "advisor_review_pack.md").exists())
            self.assertTrue((output_dir / "advisor_review_pack_ko.md").exists())
            self.assertTrue((output_dir / "reviewer_pack.md").exists())
            self.assertTrue((output_dir / "reviewer_pack_ko.md").exists())
            self.assertTrue((output_dir / "interview_pack.md").exists())
            self.assertTrue((output_dir / "interview_pack_ko.md").exists())
            self.assertTrue((output_dir / "portfolio_pack.md").exists())
            self.assertTrue((output_dir / "portfolio_pack_ko.md").exists())
            self.assertTrue((output_dir / "paper_case_table.tex").exists())
            self.assertTrue((output_dir / "paper_scenario_table.tex").exists())
            self.assertTrue((output_dir / "paper_ablation_current_table.tex").exists())
            self.assertTrue((output_dir / "paper_figure_captions.md").exists())
            self.assertTrue((output_dir / "paper_figure_captions_ko.md").exists())
            self.assertTrue((output_dir / "paper_summary_note.md").exists())
            self.assertTrue((output_dir / "paper_summary_note_ko.md").exists())
            self.assertTrue((output_dir / "paper_full_draft.md").exists())
            self.assertTrue((output_dir / "paper_full_draft_ko.md").exists())
            self.assertTrue((output_dir / "paper_full_draft.tex").exists())
            self.assertTrue((output_dir / "paper_results_section.md").exists())
            self.assertTrue((output_dir / "paper_results_section_ko.md").exists())
            self.assertTrue((output_dir / "paper_results_section.tex").exists())
            self.assertTrue((output_dir / "paper_methods_section.md").exists())
            self.assertTrue((output_dir / "paper_methods_section_ko.md").exists())
            self.assertTrue((output_dir / "paper_methods_section.tex").exists())
            self.assertTrue((output_dir / "paper_discussion_section.md").exists())
            self.assertTrue((output_dir / "paper_discussion_section_ko.md").exists())
            self.assertTrue((output_dir / "paper_discussion_section.tex").exists())
            self.assertTrue((output_dir / "paper_appendix.md").exists())
            self.assertTrue((output_dir / "paper_appendix_ko.md").exists())
            self.assertTrue((output_dir / "paper_appendix.tex").exists())
            self.assertTrue((output_dir / "paper_summary_note_en.md").exists())
            self.assertTrue((output_dir / "paper_figure_captions_en.md").exists())
            self.assertTrue((output_dir / "paper_full_draft_en.md").exists())
            self.assertTrue((output_dir / "paper_results_section_en.md").exists())
            self.assertTrue((output_dir / "paper_methods_section_en.md").exists())
            self.assertTrue((output_dir / "paper_discussion_section_en.md").exists())
            first_case = manifest_payload["cases"][0]
            self.assertTrue((output_dir / first_case["snapshot_relpath"]).exists())
            self.assertTrue((output_dir / first_case["result_relpath"]).exists())
            self.assertTrue((output_dir / first_case["report_relpath"]).exists())
            self.assertTrue((output_dir / first_case["image_relpath"]).exists())
            self.assertEqual(set(first_case["scenario_image_relpaths"].keys()), {"slowdown", "current", "speedup"})
            self.assertTrue((output_dir / first_case["scenario_image_relpaths"]["slowdown"]).exists())
            self.assertTrue((output_dir / first_case["scenario_image_relpaths"]["current"]).exists())
            self.assertTrue((output_dir / first_case["scenario_image_relpaths"]["speedup"]).exists())


if __name__ == "__main__":
    unittest.main()
