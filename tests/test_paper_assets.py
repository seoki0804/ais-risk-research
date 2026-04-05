from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.config import load_config
from ais_risk.csv_tools import preprocess_ais_csv
from ais_risk.demo_package import build_recommended_demo_package_from_csv
from ais_risk.paper_assets import build_paper_assets_from_manifest_path
from ais_risk.trajectory import reconstruct_trajectory_csv


class PaperAssetsTest(unittest.TestCase):
    def test_paper_assets_can_be_generated_from_manifest(self) -> None:
        root = Path(__file__).resolve().parents[1]
        input_path = root / "examples" / "sample_ais.csv"
        config_path = root / "configs" / "base.toml"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            tracks_path = Path(temp_dir) / "tracks.csv"
            output_dir = Path(temp_dir) / "demo"
            preprocess_ais_csv(input_path, curated_path)
            reconstruct_trajectory_csv(curated_path, tracks_path)
            build_recommended_demo_package_from_csv(
                input_path=tracks_path,
                config=load_config(config_path),
                output_dir=output_dir,
                radius_nm=6.0,
                top_n=2,
            )

            payload = build_paper_assets_from_manifest_path(output_dir / "manifest.json")
            self.assertTrue(Path(payload["paper_case_csv_path"]).exists())
            self.assertTrue(Path(payload["paper_scenario_csv_path"]).exists())
            self.assertTrue(Path(payload["paper_ablation_csv_path"]).exists())
            self.assertTrue(Path(payload["artifact_catalog_csv_path"]).exists())
            self.assertTrue(Path(payload["artifact_catalog_md_path"]).exists())
            self.assertTrue(Path(payload["artifact_catalog_ko_md_path"]).exists())
            self.assertTrue(Path(payload["audience_guide_path"]).exists())
            self.assertTrue(Path(payload["audience_guide_ko_path"]).exists())
            self.assertTrue(Path(payload["handoff_checklist_path"]).exists())
            self.assertTrue(Path(payload["handoff_checklist_ko_path"]).exists())
            self.assertTrue(Path(payload["deliverable_readiness_path"]).exists())
            self.assertTrue(Path(payload["deliverable_readiness_ko_path"]).exists())
            self.assertTrue(Path(payload["paper_case_tex_path"]).exists())
            self.assertTrue(Path(payload["paper_scenario_tex_path"]).exists())
            self.assertTrue(Path(payload["paper_ablation_tex_path"]).exists())
            self.assertTrue(Path(payload["paper_claim_matrix_csv_path"]).exists())
            self.assertTrue(Path(payload["paper_claim_matrix_md_path"]).exists())
            self.assertTrue(Path(payload["paper_claim_matrix_ko_md_path"]).exists())
            self.assertTrue(Path(payload["paper_reviewer_faq_path"]).exists())
            self.assertTrue(Path(payload["paper_reviewer_faq_ko_path"]).exists())
            self.assertTrue(Path(payload["presentation_outline_path"]).exists())
            self.assertTrue(Path(payload["presentation_outline_ko_path"]).exists())
            self.assertTrue(Path(payload["demo_talk_track_path"]).exists())
            self.assertTrue(Path(payload["demo_talk_track_ko_path"]).exists())
            self.assertTrue(Path(payload["defense_packet_path"]).exists())
            self.assertTrue(Path(payload["defense_packet_ko_path"]).exists())
            self.assertTrue(Path(payload["portfolio_case_study_path"]).exists())
            self.assertTrue(Path(payload["portfolio_case_study_ko_path"]).exists())
            self.assertTrue(Path(payload["interview_answer_bank_path"]).exists())
            self.assertTrue(Path(payload["interview_answer_bank_ko_path"]).exists())
            self.assertTrue(Path(payload["advisor_review_pack_path"]).exists())
            self.assertTrue(Path(payload["reviewer_pack_path"]).exists())
            self.assertTrue(Path(payload["interview_pack_path"]).exists())
            self.assertTrue(Path(payload["portfolio_pack_path"]).exists())
            self.assertTrue(Path(payload["paper_figure_captions_path"]).exists())
            self.assertTrue(Path(payload["paper_figure_captions_ko_path"]).exists())
            self.assertTrue(Path(payload["paper_summary_note_path"]).exists())
            self.assertTrue(Path(payload["paper_summary_note_ko_path"]).exists())
            self.assertTrue(Path(payload["paper_full_draft_path"]).exists())
            self.assertTrue(Path(payload["paper_full_draft_ko_path"]).exists())
            self.assertTrue(Path(payload["paper_full_draft_tex_path"]).exists())
            self.assertTrue(Path(payload["paper_results_section_path"]).exists())
            self.assertTrue(Path(payload["paper_results_section_ko_path"]).exists())
            self.assertTrue(Path(payload["paper_results_section_tex_path"]).exists())
            self.assertTrue(Path(payload["paper_methods_section_path"]).exists())
            self.assertTrue(Path(payload["paper_methods_section_ko_path"]).exists())
            self.assertTrue(Path(payload["paper_methods_section_tex_path"]).exists())
            self.assertTrue(Path(payload["paper_discussion_section_path"]).exists())
            self.assertTrue(Path(payload["paper_discussion_section_ko_path"]).exists())
            self.assertTrue(Path(payload["paper_discussion_section_tex_path"]).exists())
            self.assertTrue(Path(payload["paper_appendix_md_path"]).exists())
            self.assertTrue(Path(payload["paper_appendix_ko_md_path"]).exists())
            self.assertTrue(Path(payload["paper_appendix_tex_path"]).exists())

            captions = Path(payload["paper_figure_captions_path"]).read_text(encoding="utf-8")
            self.assertIn("Figure 1", captions)
            self.assertIn("Table 2", captions)
            captions_ko = Path(payload["paper_figure_captions_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("그림 1", captions_ko)
            summary_ko = Path(payload["paper_summary_note_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("Failure Case Notes", summary_ko)
            self.assertIn("Ablation 해석 Bullet", summary_ko)
            full_draft_en = Path(payload["paper_full_draft_path"]).read_text(encoding="utf-8")
            self.assertIn("## Abstract", full_draft_en)
            self.assertIn("## Introduction", full_draft_en)
            self.assertIn("## Conclusion", full_draft_en)
            full_draft_ko = Path(payload["paper_full_draft_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("## Methods", full_draft_ko)
            self.assertIn("## Discussion", full_draft_ko)
            full_draft_tex = Path(payload["paper_full_draft_tex_path"]).read_text(encoding="utf-8")
            self.assertIn("\\begin{abstract}", full_draft_tex)
            self.assertIn("\\section{Introduction}", full_draft_tex)
            self.assertIn("\\section{Conclusion}", full_draft_tex)
            claim_matrix = Path(payload["paper_claim_matrix_md_path"]).read_text(encoding="utf-8")
            self.assertIn("C1", claim_matrix)
            self.assertIn("must_not_overclaim", claim_matrix)
            faq_ko = Path(payload["paper_reviewer_faq_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("Q1.", faq_ko)
            self.assertIn("AIS-only", faq_ko)
            presentation_ko = Path(payload["presentation_outline_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("Slide 1. 문제 정의", presentation_ko)
            talk_track_ko = Path(payload["demo_talk_track_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("## 1. 오프닝", talk_track_ko)
            defense_packet_ko = Path(payload["defense_packet_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("## 30초 설명", defense_packet_ko)
            self.assertIn("## 주장해도 되는 것", defense_packet_ko)
            portfolio_case_ko = Path(payload["portfolio_case_study_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("## 프로젝트 요약", portfolio_case_ko)
            answer_bank_ko = Path(payload["interview_answer_bank_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("## Q1. 왜 이 문제를 선택했나요?", answer_bank_ko)
            advisor_pack = Path(payload["advisor_review_pack_path"]).read_text(encoding="utf-8")
            self.assertIn("Advisor Review Pack", advisor_pack)
            reviewer_pack = Path(payload["reviewer_pack_path"]).read_text(encoding="utf-8")
            self.assertIn("Reviewer Pack", reviewer_pack)
            catalog_md = Path(payload["artifact_catalog_md_path"]).read_text(encoding="utf-8")
            self.assertIn("Artifact Catalog", catalog_md)
            self.assertIn("Defense packet", catalog_md)
            audience_guide_ko = Path(payload["audience_guide_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("## 교수 / 지도교수", audience_guide_ko)
            self.assertIn("`paper_full_draft_ko.md`", audience_guide_ko)
            handoff_ko = Path(payload["handoff_checklist_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("## 논문 제출 준비", handoff_ko)
            readiness_ko = Path(payload["deliverable_readiness_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("상태: ready_for_review", readiness_ko)
            results_en = Path(payload["paper_results_section_path"]).read_text(encoding="utf-8")
            self.assertIn("Representative High-Risk Cases", results_en)
            results_ko = Path(payload["paper_results_section_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("대표 고위험 사례", results_ko)
            results_tex = Path(payload["paper_results_section_tex_path"]).read_text(encoding="utf-8")
            self.assertIn("\\section{Results}", results_tex)
            self.assertIn("\\subsection{Scenario-Level Spatial Risk Comparison}", results_tex)
            methods_en = Path(payload["paper_methods_section_path"]).read_text(encoding="utf-8")
            self.assertIn("Rule-Based Risk Baseline", methods_en)
            methods_ko = Path(payload["paper_methods_section_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("규칙 기반 위험도 baseline", methods_ko)
            methods_tex = Path(payload["paper_methods_section_tex_path"]).read_text(encoding="utf-8")
            self.assertIn("\\section{Methods}", methods_tex)
            discussion_en = Path(payload["paper_discussion_section_path"]).read_text(encoding="utf-8")
            self.assertIn("### Limitations", discussion_en)
            discussion_ko = Path(payload["paper_discussion_section_ko_path"]).read_text(encoding="utf-8")
            self.assertIn("### 한계", discussion_ko)
            discussion_tex = Path(payload["paper_discussion_section_tex_path"]).read_text(encoding="utf-8")
            self.assertIn("\\section{Discussion}", discussion_tex)
            latex_text = Path(payload["paper_scenario_tex_path"]).read_text(encoding="utf-8")
            self.assertIn("\\begin{table}", latex_text)
            self.assertIn("\\caption{Package-level scenario comparison.}", latex_text)
            appendix_text = Path(payload["paper_appendix_tex_path"]).read_text(encoding="utf-8")
            self.assertIn("\\input{paper_case_table.tex}", appendix_text)
            self.assertIn("\\section*{Appendix: AIS Risk Mapping Demo Outputs}", appendix_text)
            appendix_ko_text = Path(payload["paper_appendix_ko_md_path"]).read_text(encoding="utf-8")
            self.assertIn("논문 부록 초안", appendix_ko_text)

            manifest = json.loads(Path(payload["paper_assets_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("paper_case_csv_path", manifest)


if __name__ == "__main__":
    unittest.main()
