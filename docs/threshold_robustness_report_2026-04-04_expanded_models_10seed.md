# Threshold Robustness Report (Recommended Models)

## Inputs

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- run_manifest_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_run_manifest.csv`
- threshold_grid_size: `19`
- cost_profiles: `balanced:1:1,fn_heavy:1:3,fn_very_heavy:1:5,fp_heavy:3:1`

## Summary

| Dataset | Model | Profile | Runs | Mean Best Th | Mean Rec Th | Mean Regret | Max Regret | Regret=0 Rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| houston_pooled_pairwise | hgbt | balanced | 10 | 0.9500 | 0.9500 | 0.000 | 0.000 | 1.0000 |
| houston_pooled_pairwise | hgbt | fn_heavy | 10 | 0.2000 | 0.9500 | 12.000 | 12.000 | 0.0000 |
| houston_pooled_pairwise | hgbt | fn_very_heavy | 10 | 0.0500 | 0.9500 | 26.000 | 26.000 | 0.0000 |
| houston_pooled_pairwise | hgbt | fp_heavy | 10 | 0.9500 | 0.9500 | 0.000 | 0.000 | 1.0000 |
| nola_pooled_pairwise | hgbt | balanced | 10 | 0.9500 | 0.3500 | 16.000 | 16.000 | 0.0000 |
| nola_pooled_pairwise | hgbt | fn_heavy | 10 | 0.4000 | 0.3500 | 3.000 | 3.000 | 0.0000 |
| nola_pooled_pairwise | hgbt | fn_very_heavy | 10 | 0.3000 | 0.3500 | 2.000 | 2.000 | 0.0000 |
| nola_pooled_pairwise | hgbt | fp_heavy | 10 | 0.9500 | 0.3500 | 86.000 | 86.000 | 0.0000 |
| seattle_pooled_pairwise | extra_trees | balanced | 10 | 0.5650 | 0.6050 | 1.700 | 5.000 | 0.4000 |
| seattle_pooled_pairwise | extra_trees | fn_heavy | 10 | 0.4500 | 0.6050 | 13.800 | 30.000 | 0.0000 |
| seattle_pooled_pairwise | extra_trees | fn_very_heavy | 10 | 0.3650 | 0.6050 | 30.800 | 60.000 | 0.0000 |
| seattle_pooled_pairwise | extra_trees | fp_heavy | 10 | 0.7100 | 0.6050 | 5.300 | 11.000 | 0.2000 |

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed_detail.csv`
- summary_csv: `/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed.md`
- summary_json: `/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed.json`
