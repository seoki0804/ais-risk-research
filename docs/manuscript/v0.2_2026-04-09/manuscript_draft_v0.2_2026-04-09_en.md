# AIS Collision-Risk Heatmap Manuscript Draft v0.2 (English)

## 1. Objective
This study evaluates whether AIS-based model training can estimate area-level collision risk and support navigation decisions through heatmap + contour visualization.

## 2. Data and Experimental Setup
- Datasets: Houston, NOLA, Seattle pooled pairwise
- Model families: tabular + regional_raster_cnn + rule baseline
- Validation: in-time, out-of-time, cross-region transfer, and calibration (ECE)

## 3. Final Model Selection (10-seed)

| region | model_family | model_name | f1_mean_10seed | ece_mean_10seed | f1_single_eval | ece_single_eval |
| --- | --- | --- | --- | --- | --- | --- |
| houston | tabular | hgbt | 0.8286 | 0.0229 | 0.8286 | 0.0229 |
| nola | tabular | hgbt | 0.6015 | 0.0237 | 0.6015 | 0.0237 |
| seattle | tabular | extra_trees | 0.8174 | 0.0300 | 0.8148 | 0.0289 |

Interpretation: all three regions satisfy the ECE gate, and the final model is chosen by performance/variance tradeoff. `hgbt` is selected for Houston and NOLA, while `extra_trees` is selected for Seattle.

## 4. Core Transfer Performance

| source_region | target_region | recommended_model | delta_f1 | target_ece |
| --- | --- | --- | --- | --- |
| houston | nola | hgbt | -0.1383 | 0.0246 |
| houston | seattle | hgbt | -0.2103 | 0.0428 |
| nola | houston | hgbt | +0.3213 | 0.0159 |
| nola | seattle | hgbt | +0.4439 | 0.0260 |
| seattle | houston | extra_trees | +0.0021 | 0.0332 |
| seattle | nola | extra_trees | +0.0488 | 0.0272 |

Interpretation: Houston as source shows negative ΔF1 (domain-shift stress), while NOLA/Seattle sources show positive or near-neutral transfer outcomes.

## 5. Figure Set
- Figure 1: ![model-family](figure_1_model_family_comparison.svg)
- Figure 2: ![transfer-heatmap](figure_2_transfer_delta_f1_heatmap.svg)
- Figure 3: ![pipeline](figure_3_pipeline_overview.svg)

## 6. Terminology Mapping (KOR/ENG)

| concept | korean_term | english_term | usage_note_ko | usage_note_en |
| --- | --- | --- | --- | --- |
| Collision Risk Heatmap | 충돌위험 히트맵 | collision-risk heatmap | 공간 격자에서 상대 위험도를 색상 강도로 표현한 지도 | A map that encodes relative risk intensity over spatial grids. |
| Safety Contour | 안전도 등고선 | safety contour | 동일 위험 임계값을 연결한 곡선; 의사결정 경계로 사용 | A curve connecting equal-risk thresholds for decision boundaries. |
| Cross-Region Transfer | 교차 해역 전이 | cross-region transfer | source 해역 학습모델을 target 해역에 적용한 일반화 성능 평가 | Generalization test applying a source-region-trained model to a target region. |
| Domain Shift | 도메인 시프트 | domain shift | 학습/적용 해역 분포 차이로 성능이 변하는 현상 | Performance drift caused by source-target distribution mismatch. |
| Expected Calibration Error | 기대 보정 오차 | expected calibration error (ECE) | 예측 확률과 실제 빈도의 불일치 정도; 낮을수록 바람직 | Mismatch between predicted confidence and empirical frequency; lower is better. |
| Threshold Governance | 임계값 거버넌스 | threshold governance | 운영 임계값 변경 시 근거/승인/추적 규칙 | Policy for rationale, approval, and traceability of threshold changes. |
| Own Ship | 자선(own ship) | own ship | 분석 기준 선박. 최초 등장 시 자선(own ship)으로 병기 | Reference vessel in analysis; write as 자선(own ship) on first Korean mention. |
| Rule Baseline | 규칙 기반 기준선 | rule baseline | 모델 성능 비교를 위한 비학습 규칙 기반 참조선 | Non-learning reference baseline for model-comparison benchmarking. |

Detailed terminology guidance is provided in `terminology_mapping_v0.2_2026-04-09.md`.

## 7. Bilingual Figure Captions
- KOR/ENG caption set: `figure_captions_bilingual_v0.2_2026-04-09.md`

## 8. Scenario Visualization Evidence
- Houston scenario: `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`
- NOLA scenario: `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`
- Seattle scenario: `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`

## 9. Submission Format Note
- At this stage, authoring in `docs` is practical and reproducible.
- For venue submission, convert to the target template (Word/LaTeX) while keeping `docs/manuscript` as the single source of truth.
