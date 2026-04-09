# AIS Collision-Risk Heatmap Manuscript Draft v0.2 (English)

## 1. Objective
This study evaluates whether AIS-based model training can estimate area-level collision risk and support navigation decisions through heatmap + contour visualization.

## 2. Data, Evaluation Setup, and Governance Protocol
- Datasets: Houston, NOLA, Seattle pooled pairwise
- Model families: tabular + regional_raster_cnn + rule baseline
- Validation axes: in-time, out-of-time, cross-region transfer, and calibration (ECE)
- Seed policy: 10-seed summaries are treated as the default reporting unit

### 2.1 Data Filtering Policy
- `PP-01`: deduplicate by `mmsi + timestamp`
- `PP-02`: remove invalid latitude/longitude range records
- `PP-03`: remove `sog < 0` and screen unrealistic speed outliers
- `PP-04`: fallback from missing `heading` to `cog`
- `PP-05~PP-07`: sort by MMSI timestamp, split long gaps, and interpolate only small gaps

### 2.2 Split Policy
- Timestamp split is the baseline temporal generalization check.
- Own-ship split/LOO evaluates vessel-conditioned generalization.
- Own-ship case repeat tracks repeatability (F1 std and CI width).

### 2.3 Threshold Governance
- Model selection uses `ECE gate(<=0.1)` then `F1-first with variance tie-break` policy.
- Transfer evaluation applies the source-selected threshold unchanged on target region.
- Every threshold change is logged with rationale, approval, and performance/calibration impact.

## 3. Final Model Selection (10-seed)

| region | model_family | model_name | f1_mean_10seed | ece_mean_10seed | f1_single_eval | ece_single_eval |
| --- | --- | --- | --- | --- | --- | --- |
| houston | tabular | hgbt | 0.8286 | 0.0229 | 0.8286 | 0.0229 |
| nola | tabular | hgbt | 0.6015 | 0.0237 | 0.6015 | 0.0237 |
| seattle | tabular | extra_trees | 0.8174 | 0.0300 | 0.8148 | 0.0289 |

Interpretation: all three regions satisfy the ECE gate, and the final model is chosen by performance/variance tradeoff. `hgbt` is selected for Houston and NOLA, while `extra_trees` is selected for Seattle.

### 3.1 Uncertainty (95% CI)
| region | model_name | f1_mean_10seed | f1_std_10seed | f1_ci95_low_10seed | f1_ci95_high_10seed | ece_mean_10seed | ece_std_10seed | ece_ci95_low_10seed | ece_ci95_high_10seed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| houston | hgbt | 0.8286 | 0.0000 | 0.8286 | 0.8286 | 0.0229 | 0.0000 | 0.0229 | 0.0229 |
| nola | hgbt | 0.6015 | 0.0000 | 0.6015 | 0.6015 | 0.0237 | 0.0000 | 0.0237 | 0.0237 |
| seattle | extra_trees | 0.8174 | 0.0261 | 0.8012 | 0.8336 | 0.0300 | 0.0017 | 0.0290 | 0.0311 |

- Note: CIs use normal approximation from `f1_std/ece_std` with `n=10 seeds` assumption.

## 4. Core Transfer Performance

| source_region | target_region | recommended_model | delta_f1 | delta_f1_ci95 | target_ece |
| --- | --- | --- | --- | --- | --- |
| houston | nola | hgbt | -0.1383 | [-0.1651, -0.1145] | 0.0246 |
| houston | seattle | hgbt | -0.2103 | [-0.2395, -0.1788] | 0.0428 |
| nola | houston | hgbt | +0.3213 | [+0.2019, +0.4309] | 0.0159 |
| nola | seattle | hgbt | +0.4439 | [+0.3361, +0.5407] | 0.0260 |
| seattle | houston | extra_trees | +0.0021 | [-0.1367, +0.1413] | 0.0332 |
| seattle | nola | extra_trees | +0.0488 | [-0.0671, +0.1705] | 0.0272 |

Interpretation: Houston as source shows negative ΔF1 (domain-shift stress), while NOLA/Seattle sources show positive or near-neutral transfer outcomes.

### 4.1 Transfer Uncertainty (bootstrap 95% CI)
| source_region | target_region | recommended_model | source_f1_ci95 | target_f1_ci95 | delta_f1_ci95 | ci_method |
| --- | --- | --- | --- | --- | --- | --- |
| houston | nola | hgbt | [1.0000, 1.0000] | [0.8349, 0.8855] | [-0.1651, -0.1145] | bootstrap(n=300) |
| houston | seattle | hgbt | [1.0000, 1.0000] | [0.7605, 0.8212] | [-0.2395, -0.1788] | bootstrap(n=300) |
| nola | houston | hgbt | [0.3462, 0.4935] | [0.6954, 0.7771] | [+0.2019, +0.4309] | bootstrap(n=300) |
| nola | seattle | hgbt | [0.3462, 0.4935] | [0.8296, 0.8869] | [+0.3361, +0.5407] | bootstrap(n=300) |
| seattle | houston | extra_trees | [0.7088, 0.8916] | [0.7548, 0.8502] | [-0.1367, +0.1413] | bootstrap(n=300) |
| seattle | nola | extra_trees | [0.7088, 0.8916] | [0.8244, 0.8794] | [-0.0671, +0.1705] | bootstrap(n=300) |

- Note: transfer CIs are bootstrap estimates from source/target prediction CSVs.
- Additional caution (high-uncertainty routes): No high-uncertainty transfer route detected.

## 5. Ablation: tabular vs raster-CNN

| region | tabular_model | tabular_f1 | raster_cnn_model | raster_cnn_f1 | delta_f1_tabular_minus_cnn | tabular_ece | raster_cnn_ece | delta_ece_tabular_minus_cnn | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| houston | hgbt | 0.8286 | cnn_focal_temp | 0.8315 | -0.0029 | 0.0229 | 0.1458 | -0.1229 | trade-off or near-tie between families |
| nola | hgbt | 0.6015 | cnn_weighted | 0.4432 | +0.1583 | 0.0237 | 0.1019 | -0.0783 | tabular dominates both discrimination and calibration |
| seattle | logreg | 0.8214 | cnn_focal | 0.8364 | -0.0149 | 0.0482 | 0.2791 | -0.2310 | trade-off or near-tie between families |

Summary interpretation:
- houston: ΔF1(tabular-cnn)=-0.0029 (raster-CNN is higher), ΔECE(tabular-cnn)=-0.1229 (tabular shows better calibration).
- nola: ΔF1(tabular-cnn)=+0.1583 (tabular is higher), ΔECE(tabular-cnn)=-0.0783 (tabular shows better calibration).
- seattle: ΔF1(tabular-cnn)=-0.0149 (raster-CNN is higher), ΔECE(tabular-cnn)=-0.2310 (tabular shows better calibration).

## 6. Figure Set
- Figure 1: ![model-family](figure_1_model_family_comparison.svg)
- Figure 2: ![transfer-heatmap](figure_2_transfer_delta_f1_heatmap.svg)
- Figure 3: ![pipeline](figure_3_pipeline_overview.svg)

## 7. Terminology Mapping (KOR/ENG)

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

## 8. Bilingual Figure Captions
- KOR/ENG caption set: `figure_captions_bilingual_v0.2_2026-04-09.md`

## 9. Scenario Visualization Evidence
- Houston scenario: `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`
- NOLA scenario: `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`
- Seattle scenario: `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`

## 10. Submission Format Note
- At this stage, authoring in `docs` is practical and reproducible.
- For venue submission, convert to the target template (Word/LaTeX) while keeping `docs/manuscript` as the single source of truth.

## 11. Submission-Readiness Artifacts
- LaTeX venue template draft: `manuscript_submission_template_v0.2_2026-04-09.tex`
- Consistency audit report: `manuscript_consistency_report_v0.2_2026-04-09.md`
- Automated consistency status: `PASS` (5/5)

## 12. Prior-Work Evidence Matrix
- Evidence matrix: `prior_work_evidence_matrix_v0.2_2026-04-09.md`
- It maps each core claim to supporting literature and explicitly documents residual gaps.

## 13. Examiner-Priority TODO
- Detailed TODO: `examiner_critical_todo_v0.2_2026-04-09.md`
- This TODO prioritizes novelty framing, statistical testing, external validation scope, and operational threshold interpretation.
