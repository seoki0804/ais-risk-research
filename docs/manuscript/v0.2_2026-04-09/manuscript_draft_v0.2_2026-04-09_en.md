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

## 6. Scenario Visualization Evidence
- Houston scenario: `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`
- NOLA scenario: `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`
- Seattle scenario: `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`

## 7. Submission Format Note
- At this stage, authoring in `docs` is practical and reproducible.
- For venue submission, convert to the target template (Word/LaTeX) while keeping `docs/manuscript` as the single source of truth.
