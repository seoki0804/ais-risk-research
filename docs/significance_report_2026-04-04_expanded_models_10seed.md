# Significance Report (Recommended vs Best Alternative)

## Inputs

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- raw_rows_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_raw_rows.csv`
- bootstrap_samples: `5000`
- min_pairs: `5`

## Pairwise Delta Summary

| Dataset | Recommended | Comparator | n | ΔF1 mean (CI95) | sign p(F1) | ΔECE mean (CI95) | sign p(ECE) | F1 rec>cmp (CI) | ECE rec<cmp (CI) |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| houston_pooled_pairwise | hgbt | cnn_weighted | 10 | 0.0089 (-0.0089,0.0227) | 0.0215 | -0.1446 (-0.1609,-0.1297) | 0.0020 | False | True |
| nola_pooled_pairwise | hgbt | random_forest | 10 | 0.0613 (0.0486,0.0738) | 0.0020 | -0.0172 (-0.0182,-0.0163) | 0.0020 | True | True |
| seattle_pooled_pairwise | extra_trees | logreg | 10 | -0.0041 (-0.0201,0.0110) | 0.7539 | -0.0181 (-0.0191,-0.0171) | 0.0020 | False | True |

## Interpretation Rule

- `F1 rec>cmp (CI)=True` means the 95% CI of `(recommended - comparator)` F1 is strictly positive.
- `ECE rec<cmp (CI)=True` means the 95% CI of `(recommended - comparator)` ECE is strictly negative.
- Sign-test p-values are two-sided, computed on paired seed deltas.

## Outputs

- csv: `/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed.csv`
- md: `/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed.md`
- json: `/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed.json`
