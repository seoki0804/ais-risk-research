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
- model_names: `hgbt, rule_score`

## Model Summary

| Model | Completed Targets | Mean Target F1 | Min Target F1 | Mean ΔF1 | Max Target ECE | ECE Gate(All Targets) |
|---|---:|---:|---:|---:|---:|---|
| hgbt | 2/2 | 0.8257 | 0.7897 | -0.1743 | 0.0428 | pass |
| rule_score | 2/2 | 0.6547 | 0.5826 | 0.5436 | 0.1399 | fail |

## Recommendation

- selection_rule: `all_targets_ece_leq_max_then_max_min_target_f1_then_max_mean_target_f1_then_max_mean_delta_f1`
- recommended_model: `hgbt`

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_46/transfer_scan/houston_transfer_model_scan_detail.csv`
- model_summary_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_46/transfer_scan/houston_transfer_model_scan_model_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_46/transfer_scan/houston_transfer_model_scan.md`
- summary_json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_46/transfer_scan/houston_transfer_model_scan.json`
