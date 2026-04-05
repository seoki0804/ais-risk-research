# Transfer Model Scan

## Inputs

- source_region: `seattle`
- source_input: `/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/seattle_pooled_pairwise.csv`
- split_strategy: `own_ship`
- train_fraction: `0.6`
- val_fraction: `0.2`
- threshold_grid_step: `0.01`
- calibration_bins: `10`
- calibration_ece_max: `0.1000`
- model_names: `rule_score, logreg, hgbt, random_forest, extra_trees, torch_mlp`

## Model Summary

| Model | Completed Targets | Mean Target F1 | Min Target F1 | Mean ΔF1 | Max Target ECE | ECE Gate(All Targets) |
|---|---:|---:|---:|---:|---:|---|
| extra_trees | 2/2 | 0.8303 | 0.8070 | 0.0255 | 0.0332 | pass |
| hgbt | 2/2 | 0.8434 | 0.8108 | 0.0286 | 0.0206 | pass |
| logreg | 2/2 | 0.7158 | 0.7107 | -0.0891 | 0.0425 | pass |
| random_forest | 2/2 | 0.8469 | 0.8127 | 0.0417 | 0.0220 | pass |
| rule_score | 2/2 | 0.4472 | 0.3667 | 0.1368 | 0.1676 | fail |
| torch_mlp | 2/2 | 0.6491 | 0.5860 | -0.1561 | 0.1616 | fail |

## Recommendation

- selection_rule: `all_targets_ece_leq_max_then_max_min_target_f1_then_max_mean_target_f1_then_max_mean_delta_f1`
- recommended_model: `random_forest`

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed/seattle_transfer_model_scan_detail.csv`
- model_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed/seattle_transfer_model_scan_model_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed/seattle_transfer_model_scan.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed/seattle_transfer_model_scan.json`
