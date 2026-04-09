# AIS Risk Mapping Document Package

이 폴더는 `AIS 데이터 기반 자선(Own Ship) 중심 동적 위험도 히트맵 및 Safety Contour 생성 시스템`의 개발·연구 착수용 문서 패키지다.

## 문서 목록

1. [00_document_strategy.md](/Users/seoki/Desktop/research/docs/00_document_strategy.md)
2. [01_project_charter.md](/Users/seoki/Desktop/research/docs/01_project_charter.md)
3. [02_prd.md](/Users/seoki/Desktop/research/docs/02_prd.md)
4. [03_technical_design.md](/Users/seoki/Desktop/research/docs/03_technical_design.md)
5. [04_data_modeling_spec.md](/Users/seoki/Desktop/research/docs/04_data_modeling_spec.md)
6. [05_risk_definition_spec.md](/Users/seoki/Desktop/research/docs/05_risk_definition_spec.md)
7. [06_research_proposal.md](/Users/seoki/Desktop/research/docs/06_research_proposal.md)
8. [07_experiment_plan.md](/Users/seoki/Desktop/research/docs/07_experiment_plan.md)
9. [08_uiux_requirements.md](/Users/seoki/Desktop/research/docs/08_uiux_requirements.md)
10. [09_roadmap_and_milestones.md](/Users/seoki/Desktop/research/docs/09_roadmap_and_milestones.md)
11. [10_risk_register.md](/Users/seoki/Desktop/research/docs/10_risk_register.md)
12. [11_one_page_summary.md](/Users/seoki/Desktop/research/docs/11_one_page_summary.md)
13. [12_top_10_decisions.md](/Users/seoki/Desktop/research/docs/12_top_10_decisions.md)
14. [13_execution_checklist.md](/Users/seoki/Desktop/research/docs/13_execution_checklist.md)
15. [14_quality_review.md](/Users/seoki/Desktop/research/docs/14_quality_review.md)
16. [15_data_collection_and_model_iteration_plan.md](/Users/seoki/Desktop/research/docs/15_data_collection_and_model_iteration_plan.md)
17. [16_validation_strategy_upgrade.md](/Users/seoki/Desktop/research/docs/16_validation_strategy_upgrade.md)
18. [17_research_log_guide.md](/Users/seoki/Desktop/research/docs/17_research_log_guide.md)
19. [18_public_ais_source_shortlist.md](/Users/seoki/Desktop/research/docs/18_public_ais_source_shortlist.md)
20. [19_dma_first_dataset_runbook.md](/Users/seoki/Desktop/research/docs/19_dma_first_dataset_runbook.md)
21. [20_validation_protocol_v2.md](/Users/seoki/Desktop/research/docs/20_validation_protocol_v2.md)
22. [21_noaa_first_dataset_runbook.md](/Users/seoki/Desktop/research/docs/21_noaa_first_dataset_runbook.md)
23. [23_rotating_own_ship_learning_protocol.md](/Users/seoki/Desktop/research/docs/23_rotating_own_ship_learning_protocol.md)

## 공통 기준선

- [확정] 프로젝트의 1차 목적은 `항해 위험도 인지 및 의사결정 지원(Decision Support)`이며, `완전자율운항 제어`는 범위 밖이다.
- [확정] 데이터 범위는 `공개 AIS 데이터`로 제한한다.
- [합리적 가정] 초기 수행 형태는 `1인, 12주, 규칙 기반 우선, 노트북 기반 분석 + 경량 웹 데모`다.
- [합리적 가정] 기본 분석 단위는 `단일 혼잡 해역 1곳`, `연속 4주 AIS`, `일반 상선(Cargo Vessel) 가상 자선`이다.
- [합리적 가정] 기본 시나리오는 `현재 속력`, `20% 감속`, `20% 증속` 3종이며, 자선의 `침로(Heading/COG)는 고정`한다.
- [추가 검증 필요] 실제 대상 해역, 데이터 소스, 라이선스, 전문가 검증 채널은 착수 직후 확정해야 한다.

## 논문 초안/도식 패키지

- 논문 초안 v0.2 (Korean): [manuscript_draft_v0.2_2026-04-09_ko.md](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/manuscript_draft_v0.2_2026-04-09_ko.md)
- 논문 초안 v0.2 (English): [manuscript_draft_v0.2_2026-04-09_en.md](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/manuscript_draft_v0.2_2026-04-09_en.md)
- 논문 TODO: [manuscript_todo_v0.2_2026-04-09.md](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/manuscript_todo_v0.2_2026-04-09.md)
- 용어 매핑(KOR/ENG): [terminology_mapping_v0.2_2026-04-09.md](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/terminology_mapping_v0.2_2026-04-09.md)
- 이중언어 그림 캡션: [figure_captions_bilingual_v0.2_2026-04-09.md](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/figure_captions_bilingual_v0.2_2026-04-09.md)
- 전이 불확실성 요약(CSV): [transfer_uncertainty_summary.csv](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/transfer_uncertainty_summary.csv)
- tabular vs CNN 절제요약(CSV): [ablation_tabular_vs_cnn_summary.csv](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/ablation_tabular_vs_cnn_summary.csv)
- LaTeX 제출 템플릿: [manuscript_submission_template_v0.2_2026-04-09.tex](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/manuscript_submission_template_v0.2_2026-04-09.tex)
- 정합성 점검 리포트: [manuscript_consistency_report_v0.2_2026-04-09.md](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/manuscript_consistency_report_v0.2_2026-04-09.md)
- 영문 원고 DOCX: [manuscript_draft_v0.2_2026-04-09_en.docx](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/manuscript_draft_v0.2_2026-04-09_en.docx)
- 국문 원고 DOCX: [manuscript_draft_v0.2_2026-04-09_ko.docx](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/manuscript_draft_v0.2_2026-04-09_ko.docx)
- 정합성 리포트 DOCX: [manuscript_consistency_report_v0.2_2026-04-09.docx](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/manuscript_consistency_report_v0.2_2026-04-09.docx)
- 제출 번들 ZIP: [submission_bundle_v0.2_2026-04-09.zip](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/submission_bundle_v0.2_2026-04-09.zip)
- 제출 번들 매니페스트(SHA-256): [submission_bundle_manifest_v0.2_2026-04-09.txt](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/submission_bundle_manifest_v0.2_2026-04-09.txt)
- 그림 인덱스: [figure_index.md](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/figure_index.md)
- 모델 패밀리 비교 도식(SVG): [figure_1_model_family_comparison.svg](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/figure_1_model_family_comparison.svg)
- 전이 성능 히트맵(SVG): [figure_2_transfer_delta_f1_heatmap.svg](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/figure_2_transfer_delta_f1_heatmap.svg)
- 연구 파이프라인 도식(SVG): [figure_3_pipeline_overview.svg](/Users/seoki/Desktop/research/docs/manuscript/v0.2_2026-04-09/figure_3_pipeline_overview.svg)
- 생성 명령: `examples/run_manuscript_enhancement_pack_2026-04-09.sh`
- DOCX 변환 명령: `examples/run_manuscript_docx_export_2026-04-09.sh`
- 제출 번들 생성 명령: `examples/run_manuscript_submission_bundle_2026-04-09.sh`
- 제출 번들 검증 명령: `examples/run_manuscript_submission_verify_2026-04-09.sh`
- CI: `Research Validation Gate` 워크플로에서 제출 번들을 검증 후 artifact(`manuscript-submission-bundle-v0.2-2026-04-09`)로 업로드

## 사용 순서

1. `00`과 `01`로 범위와 가정, 성공조건을 확정한다.
2. `02`, `03`, `04`, `05`로 제품 요구사항과 구현 방법을 세부화한다.
3. `06`, `07`로 연구 질문과 실험 구조를 잠근다.
4. `08`, `09`, `10`으로 구현과 운영 리스크를 관리한다.
5. `11`, `12`, `13`, `14`로 발표, 의사결정, 착수 체크리스트, 품질 검토를 마무리한다.
6. 실데이터 단계로 넘어가면 `15`, `16`, `17`로 데이터 수집 운영, 검증 구조, 연구일지 체계를 잠근다.
7. source 선택 직전에는 `18`로 공개 AIS 소스 shortlist와 적합성 기준을 먼저 확인한다.
8. DMA 첫 실행 직전에는 `19` runbook으로 폴더/명령 순서를 고정한다.
9. 반복 실험 단계에서는 `20` 프로토콜로 합격/중단 기준을 고정한다.
10. DMA 수집 장애 시에는 `21` runbook으로 NOAA fallback 경로를 바로 사용한다.
11. 기준 선박을 바꿔가며 학습/검증하려면 `23` 프로토콜을 기본선으로 사용한다.
12. auto-selected own-ship 후보 품질을 먼저 걸러야 하면 `focus_seed_pipeline_cli --auto-candidate-quality-gate-apply` 또는 `own_ship_quality_gate_cli`를 함께 사용한다.
