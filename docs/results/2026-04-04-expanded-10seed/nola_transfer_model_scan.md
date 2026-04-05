# Transfer Model Scan

## Inputs

- source_region: `nola`
- source_input: `/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/nola_pooled_pairwise.csv`
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
| extra_trees | 2/2 | 0.7527 | 0.6935 | 0.4349 | 0.0534 | pass |
| hgbt | 2/2 | 0.7964 | 0.7351 | 0.3826 | 0.0260 | pass |
| logreg | 2/2 | 0.6447 | 0.4946 | 0.4035 | 0.0800 | pass |
| random_forest | 2/2 | 0.7606 | 0.6977 | 0.3856 | 0.0380 | pass |
| rule_score | 2/2 | 0.6142 | 0.5517 | 0.1466 | 0.1676 | fail |
| torch_mlp | 2/2 | 0.6933 | 0.6465 | 0.3499 | 0.1813 | fail |

## Recommendation

- selection_rule: `all_targets_ece_leq_max_then_max_min_target_f1_then_max_mean_target_f1_then_max_mean_delta_f1`
- recommended_model: `hgbt`

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed/nola_transfer_model_scan_detail.csv`
- model_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed/nola_transfer_model_scan_model_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed/nola_transfer_model_scan.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed/nola_transfer_model_scan.json`
