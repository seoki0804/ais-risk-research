# Figure Index (Paper Upgrade)

- Figure 1: `./figure_1_model_family_comparison.svg`
- Figure 2: `./figure_2_transfer_delta_f1_heatmap.svg`
- Figure 3: `./figure_3_pipeline_overview.svg`
- Quantitative appendix tables:
  - `./recommended_models_summary.csv`
  - `./transfer_core_summary.csv`
  - `./transfer_uncertainty_summary.csv`
  - `./transfer_route_repeated_randomization_significance_summary.csv`
  - `./out_of_domain_validation_detail_summary.csv`
  - `./out_of_domain_validation_summary.csv`
  - `./ablation_tabular_vs_cnn_summary.csv`
- Submission-readiness artifacts:
  - `./manuscript_submission_template_v0.2_2026-04-09.tex`
  - `./manuscript_consistency_report_v0.2_2026-04-09.md`
- Existing scenario visuals:
  - `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`
  - `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`
  - `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`

## Scenario Panel Table

| region | model_name | f1_mean | ece | fp | fn | reliability_figure_path | heatmap_contour_figure_svg_path | calibration_note | error_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| houston | hgbt | 0.8285714285714286 | 0.022859754716981193 | 1 | 11 | /Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/houston_recommended_reliability.png | /Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/houston_report_figure.svg | Well-calibrated probability profile (ECE <= 0.03). | FN pressure dominates; discuss missed-risk implications. |
| nola | hgbt | 0.6015037593984962 | 0.023666900072939465 | 43 | 10 | /Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/nola_recommended_reliability.png | /Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/nola_report_figure.svg | Well-calibrated probability profile (ECE <= 0.03). | FP pressure dominates; discuss alert fatigue tradeoff. |
| seattle | extra_trees | 0.8173697467009166 | 0.028175486223278014 | 5 | 15 | /Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/seattle_recommended_reliability.png | /Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/seattle_report_figure.svg | Well-calibrated probability profile (ECE <= 0.03). | FN pressure dominates; discuss missed-risk implications. |
