# Cross-Region Transfer Recommendation Check

## Inputs

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- split_strategy: `own_ship`
- train_fraction: `0.6`
- val_fraction: `0.2`
- threshold_grid_step: `0.01`
- calibration_bins: `10`

## Results

| Source | Target | Model | Status | Source F1 | Target F1 | ΔF1 | Source AUROC | Target AUROC | ΔAUROC | Target ECE |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| houston | nola | hgbt | completed | 1.0000 | 0.8617 | -0.1383 | 1.0000 | 0.9824 | -0.0176 | 0.0246 |
| houston | seattle | hgbt | completed | 1.0000 | 0.7897 | -0.2103 | 1.0000 | 0.9691 | -0.0309 | 0.0428 |
| nola | houston | hgbt | completed | 0.4138 | 0.7351 | 0.3213 | 0.9719 | 0.9736 | 0.0017 | 0.0159 |
| nola | seattle | hgbt | completed | 0.4138 | 0.8577 | 0.4439 | 0.9719 | 0.9763 | 0.0044 | 0.0260 |
| seattle | houston | extra_trees | completed | 0.8049 | 0.8070 | 0.0021 | 0.9635 | 0.9777 | 0.0142 | 0.0332 |
| seattle | nola | extra_trees | completed | 0.8049 | 0.8537 | 0.0488 | 0.9635 | 0.9850 | 0.0215 | 0.0272 |

## Outputs

- results_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv`
- results_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check_summary.json`
