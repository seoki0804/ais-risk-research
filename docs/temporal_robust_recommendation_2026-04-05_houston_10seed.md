# Temporal Robust Recommendation

## Inputs

- baseline_aggregate_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv`
- out_of_time_aggregate_csv: `/Users/seoki/Desktop/research/outputs/2026-04-05_houston_timestamp_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv`
- baseline_recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- dataset_prefix_filters: `houston`
- f1_tolerance: `0.0100`
- max_ece_mean: `0.1000`
- min_out_of_time_delta_f1: `-0.0500`
- delta_penalty_weight: `1.0000`

## Summary

- dataset_count: `1`
- changed_recommendation_count: `0`
- temporal_target_pass(current->robust): `0 -> 0`
- temporal_target_feasible_datasets(any model / ece-pass model): `1 / 0`
- best observed out-of-time ΔF1 (any / ece-pass): `0.0727 / -0.1013`
- max robust in-time regression from best F1: `0.0000`

## Current vs Robust

| Dataset | Current | Robust | Changed | Current ΔF1(oot-in) | Robust ΔF1(oot-in) | Robust Regression(best F1-ref) | Gate Status |
|---|---|---|---|---:|---:|---:|---|
| houston_pooled_pairwise | hgbt | hgbt | no | -0.1013 | -0.1013 | 0.0000 | temporal_gate_failed_fallback_to_f1_band_with_ece_gate |

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/docs/temporal_robust_recommendation_2026-04-05_houston_10seed_detail.csv`
- comparison_csv: `/Users/seoki/Desktop/research/docs/temporal_robust_recommendation_2026-04-05_houston_10seed_comparison.csv`
- recommendation_csv: `/Users/seoki/Desktop/research/docs/temporal_robust_recommendation_2026-04-05_houston_10seed_recommendation.csv`
- summary_md: `/Users/seoki/Desktop/research/docs/temporal_robust_recommendation_2026-04-05_houston_10seed.md`
- summary_json: `/Users/seoki/Desktop/research/docs/temporal_robust_recommendation_2026-04-05_houston_10seed.json`
