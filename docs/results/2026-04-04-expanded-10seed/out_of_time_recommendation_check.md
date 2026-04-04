# Out-of-Time Recommendation Check

## Inputs

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- baseline_leaderboard_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_multiarea_expanded/all_models_multiarea_leaderboard.csv`
- split_strategy: `timestamp`
- train_fraction: `0.6`
- val_fraction: `0.2`
- include_regional_cnn: `False`

## Results

| Region | Dataset | Model | Status | Baseline F1 | OOT F1 | ΔF1 | Baseline AUROC | OOT AUROC | ΔAUROC | Baseline ECE | OOT ECE | ΔECE |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| houston | houston_pooled_pairwise | hgbt | completed | 0.8286 | 0.7273 | -0.1013 | 0.9833 | 0.9649 | -0.0184 | 0.0229 | 0.0240 | 0.0012 |
| nola | nola_pooled_pairwise | hgbt | completed | 0.6015 | 0.8333 | 0.2318 | 0.9707 | 0.9919 | 0.0212 | 0.0237 | 0.0216 | -0.0021 |
| seattle | seattle_pooled_pairwise | extra_trees | completed | 0.8148 | 0.8049 | -0.0099 | 0.9690 | 0.9773 | 0.0083 | 0.0289 | 0.0377 | 0.0088 |

## Outputs

- results_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_out_of_time_check_10seed/out_of_time_recommendation_check.csv`
- results_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_out_of_time_check_10seed/out_of_time_recommendation_check.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_out_of_time_check_10seed/out_of_time_recommendation_check_summary.json`
