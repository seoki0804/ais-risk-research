# Cross-Region Transfer Recommendation Check

## Inputs

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_recommendation.csv`
- split_strategy: `own_ship`
- train_fraction: `0.6`
- val_fraction: `0.2`
- calibration_bins: `10`

## Results

| Source | Target | Model | Status | Source F1 | Target F1 | ΔF1 | Source AUROC | Target AUROC | ΔAUROC | Target ECE |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| houston | nola | hgbt | completed | 1.0000 | 0.8617 | -0.1383 | 1.0000 | 0.9824 | -0.0176 | 0.0246 |
| houston | seattle | hgbt | completed | 1.0000 | 0.7993 | -0.2007 | 1.0000 | 0.9691 | -0.0309 | 0.0428 |
| nola | houston | hgbt | completed | 0.4250 | 0.7403 | 0.3153 | 0.9719 | 0.9736 | 0.0017 | 0.0159 |
| nola | seattle | hgbt | completed | 0.4250 | 0.8577 | 0.4327 | 0.9719 | 0.9763 | 0.0044 | 0.0260 |
| seattle | houston | logreg | completed | 0.8148 | 0.7171 | -0.0977 | 0.9618 | 0.9653 | 0.0035 | 0.0232 |
| seattle | nola | logreg | completed | 0.8148 | 0.7050 | -0.1099 | 0.9618 | 0.9526 | -0.0092 | 0.0425 |

## Outputs

- results_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check/transfer_recommendation_check.csv`
- results_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check/transfer_recommendation_check.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check/transfer_recommendation_check_summary.json`
