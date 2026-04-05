# Houston Transfer Policy Compare (Shortlist)

## Inputs

- gap_detail_csv: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_policy_compare_all_models_10seed/houston_all_models_transfer_gap_detail.csv`
- source_region: `houston`
- shortlist: `hgbt, extra_trees, random_forest`
- policy comparison: `fixed source threshold` vs `target-retuned threshold`

## Model Summary

| Model | Pairs | Negative(Fixed) | Negative(Retuned) | Mean ΔF1 Fixed | Mean ΔF1 Retuned | Mean Retune Gain | Max Retune Gain |
|---|---:|---:|---:|---:|---:|---:|---:|
| extra_trees | 2 | 2 | 2 | -0.1754 | -0.1277 | 0.0478 | 0.0880 |
| hgbt | 2 | 2 | 2 | -0.1743 | -0.1331 | 0.0412 | 0.0793 |
| logreg | 2 | 2 | 2 | -0.2309 | -0.1945 | 0.0364 | 0.0684 |
| random_forest | 2 | 2 | 2 | -0.2049 | -0.1155 | 0.0894 | 0.1586 |
| rule_score | 2 | 0 | 0 | 0.5436 | 0.5942 | 0.0506 | 0.0940 |
| torch_mlp | 2 | 2 | 2 | -0.1763 | -0.1498 | 0.0265 | 0.0398 |

## Outputs

- summary_csv: `/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_all_models_2026-04-05_10seed.csv`
- summary_json: `/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_all_models_2026-04-05_10seed.json`
- summary_md: `/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_all_models_2026-04-05_10seed.md`
