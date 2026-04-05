# Transfer Model Scan

## Inputs

- source_region: `houston`
- source_input: `/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/houston_pooled_pairwise.csv`
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
| extra_trees | 2/2 | 0.8246 | 0.7821 | -0.1754 | 0.0887 | pass |
| hgbt | 2/2 | 0.8257 | 0.7897 | -0.1743 | 0.0428 | pass |
| logreg | 2/2 | 0.7691 | 0.7391 | -0.2309 | 0.2145 | fail |
| random_forest | 2/2 | 0.7951 | 0.7221 | -0.2049 | 0.0721 | pass |
| rule_score | 2/2 | 0.6547 | 0.5826 | 0.5436 | 0.1399 | fail |
| torch_mlp | 2/2 | 0.8237 | 0.8206 | -0.1763 | 0.2302 | fail |

## Recommendation

- selection_rule: `all_targets_ece_leq_max_then_max_min_target_f1_then_max_mean_target_f1_then_max_mean_delta_f1`
- recommended_model: `hgbt`

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan_detail.csv`
- model_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan_model_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan.json`
