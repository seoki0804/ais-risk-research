# Out-of-Time Threshold Policy Compare

## Inputs

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- baseline_leaderboard_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_multiarea_expanded/all_models_multiarea_leaderboard.csv`
- out_of_time_output_root: `/Users/seoki/Desktop/research/outputs/2026-04-04_out_of_time_check_10seed`
- dataset_prefix_filters: `houston, nola, seattle`
- threshold_grid_step: `0.0100`
- max_out_of_time_ece: `0.1000`
- min_out_of_time_delta_f1: `-0.0500`
- max_in_time_regression_from_best_f1: `0.0200`
- include_oracle_policy: `True`

## Policy Summary

| Policy | Datasets | Completed | Combined Pass | Temporal Pass | ECE Pass | In-Time Regr Pass | Mean ΔF1 | Min ΔF1 | Max OOT ECE | Max In-Time Regr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed_baseline_threshold | 3 | 3 | 2 | 3 | 3 | 2 | 0.0711 | -0.0286 | 0.0377 | 0.0215 |
| oot_oracle_threshold | 3 | 3 | 2 | 3 | 3 | 2 | 0.0877 | -0.0286 | 0.0377 | 0.0215 |
| oot_val_tuned | 3 | 3 | 1 | 2 | 3 | 2 | 0.0402 | -0.1013 | 0.0377 | 0.0215 |

## Houston Detail

| Policy | Baseline th | Policy th | Baseline F1 | OOT F1 | ΔF1 | OOT ECE | Combined Pass |
|---|---:|---:|---:|---:|---:|---:|---|
| fixed_baseline_threshold | 0.9500 | 0.9500 | 0.8286 | 0.8000 | -0.0286 | 0.0240 | yes |
| oot_oracle_threshold | 0.9500 | 0.9400 | 0.8286 | 0.8000 | -0.0286 | 0.0240 | yes |
| oot_val_tuned | 0.9500 | 0.7500 | 0.8286 | 0.7273 | -0.1013 | 0.0240 | no |

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed_detail.csv`
- policy_summary_csv: `/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed_policy_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.md`
- summary_json: `/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.json`
