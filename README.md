# AIS Risk Mapping Starter

공개 AIS만으로 자선(Own Ship) 주변 위험 공간을 시각화하는 해양 의사결정 지원 프로젝트의 구현 및 연구 저장소입니다.

`AIS-only own-ship-centric spatial risk mapping for maritime decision support`

`Pairwise AIS 위험 판단을 own-ship-centric spatial risk field로 확장`

## 한눈에 보기

- 공개 AIS 기반 `own-ship-centric spatial risk mapping`
- main evaluation은 `own_ship split`, `timestamp split`은 secondary benchmark
- `hgbt primary + logreg comparator`
- main conclusions come from CPU-based `hgbt/logreg` evaluation
- `torch_mlp` is retained only as an optional GPU comparator
- threshold는 단일 최적값이 아니라 `default / balanced / tight` shortlist
- threshold instability는 숨기지 않고 `shortlist operation`으로 보고
- 목표는 `AIS-only decision support`이며, 완전자율운항 제어는 비목표
- Houston figure를 main visual로, NOLA/Seattle을 support visual로 사용

## 프로젝트 요약

- 이 프로젝트는 공개 NOAA AIS를 활용해 자선 주변 위험도를 공간적으로 계산하고, 이를 heatmap과 safety contour로 시각화합니다.
- 핵심은 pairwise vessel-risk 신호를 own-ship-centric spatial risk field로 확장하는 것입니다.

## 공개용 한 줄 요약

- GitHub short description:
  - `공개 AIS만으로 own-ship-centric spatial risk field를 계산하는 해양 의사결정 지원 프로젝트`
- English short description:
  - `AIS-only spatial risk mapping for own-ship-centric maritime decision support`
- Short-form source:
  - [outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day/portfolio_copy_paste_sheet_61day_ko_en.md](outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day/portfolio_copy_paste_sheet_61day_ko_en.md)

## Validation Evidence

| 항목 | 값 |
|---|---|
| 검증 기간 | `2023-08-01~2023-09-15 + 2023-10-01~2023-10-15` (61일) |
| 해역 | `Houston / NOLA / Seattle` |
| 통합 pairwise rows | `67,892` |
| own_mmsi | `15` |
| 메인 평가 축 | `own_ship split` |
| 보조 benchmark | `timestamp split` |
| 주력 모델 | `hgbt` |
| comparator | `logreg` |
| main evidence | CPU-based `hgbt/logreg` |
| threshold 결론 | `single optimum`이 아니라 shortlist 운영 |

지역 failure-mode 요약:
- `Houston = date-varying but recurrent`
- `Seattle = mixed-sign and non-recurrent`
- `NOLA = mostly negative/neutral with isolated positive trade-off`

## 가장 먼저 볼 것

- 3분 요약: [outputs/presentation_one_page_61day_2026-03-13/presentation_one_page_61day.md](outputs/presentation_one_page_61day_2026-03-13/presentation_one_page_61day.md)
- 공개 페이지 초안: [PORTFOLIO_PUBLIC_PAGE.md](PORTFOLIO_PUBLIC_PAGE.md)
- 현재 상태 handoff: [outputs/presentation_deck_outline_61day_2026-03-13/project_handoff_summary_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/project_handoff_summary_61day.md)
- 대표 결과물 shortlist: [outputs/presentation_deck_outline_61day_2026-03-13/representative_outputs_manifest_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/representative_outputs_manifest_61day.md)
- 프로그램 전체 진입점: [outputs/presentation_deck_outline_61day_2026-03-13/program_master_finalization_runbook_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/program_master_finalization_runbook_61day.md)
- 전체 문서 허브: [outputs/presentation_deck_outline_61day_2026-03-13/package_index_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/package_index_61day.md)
- 검증 수치 총괄: [research_logs/2026-03-10_validation_upgrade_v3.md](research_logs/2026-03-10_validation_upgrade_v3.md)

## 대표 시각

<p align="center">
  <img src="outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day/portfolio_png_fallbacks_61day/houston_current_threshold_shortlist_compare_hero.png" alt="Houston main visual" width="760" />
</p>

- Main visual, Houston holdout compare: [outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/houston_24h_20231015/houston_24h_20231015_current_threshold_shortlist_compare.svg](outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/houston_24h_20231015/houston_24h_20231015_current_threshold_shortlist_compare.svg)
- Support visual, NOLA holdout compare: [outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/nola_24h_20231015/nola_24h_20231015_current_threshold_shortlist_compare.svg](outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/nola_24h_20231015/nola_24h_20231015_current_threshold_shortlist_compare.svg)
- Support visual, Seattle holdout compare: [outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/seattle_24h_20231015/seattle_24h_20231015_current_threshold_shortlist_compare.svg](outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/seattle_24h_20231015/seattle_24h_20231015_current_threshold_shortlist_compare.svg)
- SVG/PNG fallback 기준: [outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day/portfolio_visual_fallback_note_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day/portfolio_visual_fallback_note_61day.md)

## 외부 공개 기본값

- Project card title:
  - `AIS Spatial Risk Mapping`
- Project card subtitle:
  - `공개 AIS로 자선 주변 위험 공간을 시각화하는 해양 의사결정 지원 프로젝트`
- One-line portfolio summary:
  - `공개 AIS 기반 pairwise 위험 신호를 자선 중심 spatial risk field로 확장해 heatmap과 safety contour로 시각화한 해양 의사결정 지원 프로젝트`

## 실제 작업 진입점

- 논문 정리: [outputs/presentation_deck_outline_61day_2026-03-13/paper_finalization_packet_61day](outputs/presentation_deck_outline_61day_2026-03-13/paper_finalization_packet_61day)
- 논문 source kit: [outputs/presentation_deck_outline_61day_2026-03-13/paper_source_kit_61day](outputs/presentation_deck_outline_61day_2026-03-13/paper_source_kit_61day)
- 발표 정리: [outputs/presentation_deck_outline_61day_2026-03-13/presentation_finalization_packet_61day](outputs/presentation_deck_outline_61day_2026-03-13/presentation_finalization_packet_61day)
- 발표 제작본: [outputs/presentation_deck_outline_61day_2026-03-13/presentation_production_packet_61day](outputs/presentation_deck_outline_61day_2026-03-13/presentation_production_packet_61day)
- 발표 source kit: [outputs/presentation_deck_outline_61day_2026-03-13/presentation_source_kit_61day](outputs/presentation_deck_outline_61day_2026-03-13/presentation_source_kit_61day)
- 발표 workbench: [outputs/presentation_deck_outline_61day_2026-03-13/workbenches/presentation_workbench_main_61day](outputs/presentation_deck_outline_61day_2026-03-13/workbenches/presentation_workbench_main_61day)
- 포트폴리오 정리: [outputs/presentation_deck_outline_61day_2026-03-13/portfolio_finalization_packet_61day](outputs/presentation_deck_outline_61day_2026-03-13/portfolio_finalization_packet_61day)
- 포트폴리오 공개본: [outputs/presentation_deck_outline_61day_2026-03-13/portfolio_public_release_packet_61day](outputs/presentation_deck_outline_61day_2026-03-13/portfolio_public_release_packet_61day)
- 포트폴리오 source kit: [outputs/presentation_deck_outline_61day_2026-03-13/portfolio_source_kit_61day](outputs/presentation_deck_outline_61day_2026-03-13/portfolio_source_kit_61day)
- 포트폴리오 workbench: [outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day](outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day)
- venue-specific 제출 운영: [outputs/presentation_deck_outline_61day_2026-03-13/venue_completion_packet_61day](outputs/presentation_deck_outline_61day_2026-03-13/venue_completion_packet_61day)
- venue ops kit: [outputs/presentation_deck_outline_61day_2026-03-13/venue_ops_kit_61day](outputs/presentation_deck_outline_61day_2026-03-13/venue_ops_kit_61day)
- 최종 handoff bundle: [outputs/presentation_deck_outline_61day_2026-03-13/delivery_handoff_bundle_61day](outputs/presentation_deck_outline_61day_2026-03-13/delivery_handoff_bundle_61day)
- 상위 묶음: [outputs/presentation_deck_outline_61day_2026-03-13/master_finalization_packet_61day](outputs/presentation_deck_outline_61day_2026-03-13/master_finalization_packet_61day)
- workbench 생성 가이드: [outputs/presentation_deck_outline_61day_2026-03-13/workbench_materialization_runbook_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/workbench_materialization_runbook_61day.md)

## 이 저장소를 어떻게 볼지

- 논문 중심이면: `program master finalization runbook -> paper finalization packet -> paper consistency audit`
- 실제 논문 편집이면: `paper source kit -> compile handoff -> asset-locked tex`
- 실제 논문 compile 결과를 확인하려면: `paper workbench -> paper_compile_result_note_61day.md -> asset-locked pdf`
- 실제 논문 전달 묶음이 필요하면: `paper workbench -> paper_delivery_bundle_61day/ 또는 .zip`
- 실제 논문 검토를 바로 시작하면: `paper workbench -> paper_reviewer_final_pass_61day.md -> launch_paper_review_61day.sh`
- 실제 논문 템플릿 반영 직전이면: `paper workbench -> paper_template_insertion_final_pass_61day.md -> paper_final_signoff_sheet_61day.md -> launch_paper_template_pass_61day.sh`
- 발표 중심이면: `representative outputs manifest -> presentation finalization packet -> final presentation run sheet`
- 실제 슬라이드 제작이면: `presentation production packet -> final presentation run sheet -> rehearsal runbook`
- 실제 슬라이드 편집 handoff면: `presentation source kit -> source handoff -> production build sheet`
- 실제 슬라이드 작업을 시작하면: `presentation workbench -> presenter final pass -> production draft pptx/pdf -> preview note -> manual qc final pass -> adjustment log -> build checklist -> run sheet 분기 -> final sign-off`
- 실제 발표 전달 묶음이 필요하면: `presentation workbench -> presentation_delivery_bundle_61day/ 또는 .zip`
- 포트폴리오 중심이면: `portfolio finalization packet -> portfolio readme copy -> representative outputs manifest`
- 실제 공개 반영이면: `portfolio public release packet -> README / landing copy -> public release checklist`
- 실제 공개 페이지 handoff면: `portfolio source kit -> source handoff -> public release build sheet`
- 실제 공개 문구 작업을 시작하면: `portfolio workbench -> public release final pass -> publish-ready page -> copy-paste sheet -> asset placement -> build checklist -> final sign-off`
- 실제 GitHub/public-platform 반영이면: `portfolio workbench -> portfolio_github_final_pass_61day.md -> README.md -> PORTFOLIO_PUBLIC_PAGE.md -> width guide -> sign-off`
- 실제 공개 전달 묶음이 필요하면: `portfolio workbench -> portfolio_release_bundle_61day/ 또는 .zip`
- root source와 preview artifact를 같이 넘기려면: `portfolio workbench -> portfolio_platform_release_bundle_manifest_61day.md`
- 실제 공개 페이지 원문이 필요하면: `PORTFOLIO_PUBLIC_PAGE.md -> README -> release bundle`
- 실제 외부 공개 기본값이 필요하면: `README 외부 공개 기본값 -> portfolio copy-paste sheet -> asset placement`
- 리뷰 대응이면: `message lock sheet -> validation summary -> reviewer rebuttal packs`
- venue가 정해졌다면: `target venue intake sheet -> venue completion packet -> run_venue_packet_ops`
- 실제 venue 운영 handoff면: `venue ops kit -> ops handoff -> prepare_venue_packet -> run_venue_packet_ops`
- 실제 venue 작업을 시작하면: `venue workbench -> quick start -> notes copy-paste template -> run_venue_packet_ops`
- camera-ready 리허설 결과를 보려면: `venue workbench -> venue_camera_ready_rehearsal_note_61day.md`
- 전체를 한 번에 넘길 때는: `delivery handoff bundle -> summary -> 필요한 하위 kit`
- 실제 수정은: `workbench materialization runbook -> materialize_handoff_workbench -> workbench에서 편집`

## 이 프로젝트가 하지 않는 것

- 완전자율운항 제어
- 실제 조타 명령 자동 생성
- 법적 안전 경계 보장
- 상용 ECDIS 인증 수준 안전성
- AIS만으로 검증 불가능한 정밀 제어 주장
- 현재 기여로서의 강화학습(RL) 정책 학습 주장

## 빠른 시작

1. Python 3.11 이상 사용
2. 샘플 snapshot 실행

```bash
PYTHONPATH=src python -m ais_risk.cli \
  --snapshot examples/sample_snapshot.json \
  --config configs/base.toml \
  --output outputs/sample_result.json
```

3. raw AIS CSV -> snapshot -> risk run

```bash
PYTHONPATH=src python -m ais_risk.preprocess_cli \
  --input examples/sample_ais.csv \
  --output outputs/sample_ais_curated.csv \
  --min-lat 35.03 \
  --max-lat 35.10 \
  --min-lon 129.03 \
  --max-lon 129.10 \
  --vessel-types cargo,tanker

PYTHONPATH=src python -m ais_risk.trajectory_cli \
  --input outputs/sample_ais_curated.csv \
  --output outputs/sample_ais_tracks.csv \
  --split-gap-min 10 \
  --max-interp-gap-min 2 \
  --step-sec 30

PYTHONPATH=src python -m ais_risk.snapshot_cli \
  --input outputs/sample_ais_tracks.csv \
  --own-mmsi 440000001 \
  --timestamp 2026-03-07T09:00:00Z \
  --radius-nm 6 \
  --output outputs/from_csv_snapshot.json

PYTHONPATH=src python -m ais_risk.cli \
  --snapshot outputs/from_csv_snapshot.json \
  --config configs/base.toml \
  --output outputs/from_csv_result.json
```

더 자세한 실행 흐름:
- NOAA 실행 기준서: [docs/22_noaa_houston_quick_validation_runbook.md](docs/22_noaa_houston_quick_validation_runbook.md)
- rotating own-ship 프로토콜: [docs/23_rotating_own_ship_learning_protocol.md](docs/23_rotating_own_ship_learning_protocol.md)
- 전체 패키지 인덱스: [outputs/presentation_deck_outline_61day_2026-03-13/package_index_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/package_index_61day.md)

## 전체 모델 일괄 학습 (GitHub 재현용)

`rule_score / logreg / hgbt / random_forest / extra_trees / torch_mlp`를 한 번에 학습하고, 성능 비교표(`csv`, `md`)를 자동 생성합니다.

```bash
PYTHONPATH=src python -m ais_risk.all_models_cli \
  --input outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/houston_pooled_pairwise.csv \
  --output-dir outputs/all_models_houston_2026-03-28 \
  --split-strategy own_ship \
  --auto-adjust-split-for-support \
  --torch-device auto
```

CNN 비교군(`weighted_bce`, `focal`)까지 포함하려면:

```bash
PYTHONPATH=src python -m ais_risk.all_models_cli \
  --input outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/houston_pooled_pairwise.csv \
  --output-dir outputs/all_models_houston_with_cnn_2026-03-28 \
  --split-strategy own_ship \
  --auto-adjust-split-for-support \
  --include-regional-cnn \
  --cnn-losses weighted_bce,focal
```

주요 산출물:
- `<output-dir>/<dataset>_all_models_leaderboard.csv`
- `<output-dir>/<dataset>_all_models_leaderboard.md`
- `<output-dir>/<dataset>_all_models_run_summary.json`
- `<output-dir>/<dataset>_all_models_run_summary.md`

참고: 리더보드에는 `sample_count/positive_count/tp/fp/tn/fn`이 함께 기록되며, 양성 표본이 적으면 `low_positive_support` 경고가 notes에 표시됩니다.
`--auto-adjust-split-for-support`를 켜면 가능한 범위에서 split 비율을 자동 조정해 이 경고를 완화합니다.

3개 해역(Houston/NOLA/Seattle) 일괄 실행은:

```bash
examples/run_all_supported_models_multiarea_61day.sh
```

시드 안정성(평균/표준편차)까지 확인하려면:

```bash
PYTHONPATH=src python -m ais_risk.all_models_seed_sweep_cli \
  --output-root outputs/all_models_seed_sweep_2026-04-04 \
  --regions houston,nola,seattle \
  --seeds 41,42,43 \
  --include-regional-cnn \
  --recommendation-max-ece-mean 0.10
```

주요 안정성 산출물:
- `all_models_seed_sweep_aggregate.csv` (모델별 평균/표준편차/CI95)
- `all_models_seed_sweep_winner_summary.csv` (seed별 승자 빈도)
- `all_models_seed_sweep_recommendation.csv` (해역별 자동 추천)

참고: 추천표는 기본적으로 `ECE mean <= 0.10` 하드 게이트를 적용합니다.
비활성화하려면 `--disable-recommendation-ece-gate`를 사용하세요.

최종 제출용(권장) 10-seed 실행:

```bash
examples/run_all_models_seed_sweep_10seed_2026-04-04.sh
```

10-seed 추천을 기준으로 out-of-time/transfer/reliability/taxonomy를 한 번에 갱신하려면:

```bash
examples/run_external_validity_checks_2026-04-04_10seed.sh
```

추천 모델의 out-of-time(timestamp split) 점검:

```bash
PYTHONPATH=src python -m ais_risk.out_of_time_eval_cli \
  --output-root outputs/2026-04-04_out_of_time_check
```

주요 산출물:
- `out_of_time_recommendation_check.csv`
- `out_of_time_recommendation_check.md`

cross-region transfer 점검(소스 해역 추천모델을 타 해역으로 전이):

```bash
PYTHONPATH=src python -m ais_risk.transfer_recommendation_eval_cli \
  --output-root outputs/2026-04-04_transfer_check
```

주요 산출물:
- `transfer_recommendation_check.csv`
- `transfer_recommendation_check.md`

out-of-time + transfer + 번들 갱신을 한 번에 실행:

```bash
examples/run_external_validity_checks_2026-04-04.sh
```

위 스크립트는 reliability/taxonomy report까지 함께 생성/번들링하며,
`outputs/2026-04-04_external_validity_command_log.txt`에 실행 커맨드 로그를 남깁니다.

추천 모델 리라이어빌리티 다이어그램 생성:

```bash
PYTHONPATH=src python -m ais_risk.reliability_report_cli \
  --output-root outputs/2026-04-04_reliability_report
```

추천 모델 FP/FN taxonomy 리포트 생성:

```bash
PYTHONPATH=src python -m ais_risk.error_taxonomy_report_cli \
  --output-root outputs/2026-04-04_error_taxonomy \
  --seed 42
```

GitHub 업로드용 경량 결과 번들 추출:

```bash
examples/export_github_results_bundle_2026-04-04.sh
```

확장 모델(`random_forest`, `extra_trees`) 재실행 결과 번들은:

```bash
examples/export_github_results_bundle_2026-04-04_expanded.sh
```

10-seed 기준 최종 번들은:

```bash
examples/export_github_results_bundle_2026-04-04_expanded_10seed.sh
```

확장 번들 매니페스트는 다음을 포함합니다.
- 복사된 산출물 SHA256/파일크기
- 입력 데이터 CSV SHA256
- 실행 커맨드 로그 SHA256(`external_validity_command_log_2026-04-04.txt`)
- git commit/dirty 상태

## 저장소 구조

- `src/`: core Python package
- `configs/`: config files
- `examples/`: helper scripts and wrappers
- `outputs/`: figures, packets, presentation/manuscript assets
- `research_logs/`: running research logs
- `docs/`: runbooks and operational documents
- `tests/`: unit and smoke tests

## 현재 운영 기준

- 프로그램 전체 기준: [outputs/presentation_deck_outline_61day_2026-03-13/program_master_finalization_runbook_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/program_master_finalization_runbook_61day.md)
- packet 간 교차 감사: [outputs/presentation_deck_outline_61day_2026-03-13/cross_packet_readiness_audit_61day.md](outputs/presentation_deck_outline_61day_2026-03-13/cross_packet_readiness_audit_61day.md)
- 현재 상태 보고서: [research_logs/2026-03-10_status_report_and_next_research_plan.md](research_logs/2026-03-10_status_report_and_next_research_plan.md)
- 검증 총괄: [research_logs/2026-03-10_validation_upgrade_v3.md](research_logs/2026-03-10_validation_upgrade_v3.md)

## 다음 단계

- paper source kit 기준으로 실제 템플릿 반영
- presentation packet 기준으로 실제 슬라이드 제작
- portfolio packet 기준으로 README/landing 반영
- venue가 정해지면 venue packet을 `READY`까지 운영
