# All Models Seed Sweep Summary

## Inputs

- output_root: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded`
- regions: `houston, nola, seattle`
- seeds: `41, 42, 43`
- include_regional_cnn: `True`
- split_strategy: `own_ship`
- auto_adjust_split_for_support: `True`
- min_positive_support: `10`
- recommendation_f1_tolerance: `0.01`
- recommendation_max_ece_mean: `0.1`

## Aggregated Model Metrics

| Dataset | Model | Family | Runs | F1 mean±std | AUROC mean±std | ECE mean±std | Positive mean |
|---|---|---|---:|---:|---:|---:|---:|
| houston_pooled_pairwise | hgbt | tabular | 3 | 0.8286±0.0000 | 0.9833±0.0000 | 0.0229±0.0000 | 40.0 |
| houston_pooled_pairwise | extra_trees | tabular | 3 | 0.8169±0.0000 | 0.9758±0.0034 | 0.0378±0.0021 | 40.0 |
| houston_pooled_pairwise | random_forest | tabular | 3 | 0.8057±0.0112 | 0.9780±0.0006 | 0.0276±0.0012 | 40.0 |
| houston_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | 3 | 0.8056±0.0093 | 0.9898±0.0016 | 0.1818±0.0138 | 40.0 |
| houston_pooled_pairwise | cnn_weighted | regional_raster_cnn | 3 | 0.8054±0.0091 | 0.9898±0.0016 | 0.1788±0.0120 | 40.0 |
| houston_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | 3 | 0.8003±0.0290 | 0.9883±0.0051 | 0.1295±0.0146 | 40.0 |
| houston_pooled_pairwise | cnn_focal | regional_raster_cnn | 3 | 0.7940±0.0308 | 0.9883±0.0051 | 0.2277±0.0314 | 40.0 |
| houston_pooled_pairwise | torch_mlp | tabular | 3 | 0.7573±0.0439 | 0.9754±0.0030 | 0.2228±0.0420 | 40.0 |
| houston_pooled_pairwise | logreg | tabular | 3 | 0.7317±0.0000 | 0.9564±0.0000 | 0.0716±0.0000 | 40.0 |
| houston_pooled_pairwise | rule_score | tabular | 3 | 0.4138±0.0000 | 0.9052±0.0000 | 0.1718±0.0000 | 40.0 |
| nola_pooled_pairwise | hgbt | tabular | 3 | 0.6015±0.0000 | 0.9707±0.0000 | 0.0237±0.0000 | 50.0 |
| nola_pooled_pairwise | random_forest | tabular | 3 | 0.5237±0.0062 | 0.9670±0.0019 | 0.0409±0.0028 | 50.0 |
| nola_pooled_pairwise | extra_trees | tabular | 3 | 0.5236±0.0143 | 0.9563±0.0025 | 0.0587±0.0016 | 50.0 |
| nola_pooled_pairwise | rule_score | tabular | 3 | 0.4455±0.0000 | 0.9735±0.0000 | 0.1412±0.0000 | 50.0 |
| nola_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | 3 | 0.4277±0.0016 | 0.9599±0.0031 | 0.0894±0.0140 | 50.0 |
| nola_pooled_pairwise | logreg | tabular | 3 | 0.4248±0.0000 | 0.9204±0.0000 | 0.0531±0.0000 | 50.0 |
| nola_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | 3 | 0.4240±0.0149 | 0.9601±0.0035 | 0.0958±0.0097 | 50.0 |
| nola_pooled_pairwise | cnn_focal | regional_raster_cnn | 3 | 0.4235±0.0134 | 0.9599±0.0031 | 0.1847±0.0089 | 50.0 |
| nola_pooled_pairwise | cnn_weighted | regional_raster_cnn | 3 | 0.4184±0.0217 | 0.9601±0.0035 | 0.1093±0.0085 | 50.0 |
| nola_pooled_pairwise | torch_mlp | tabular | 3 | 0.4151±0.0428 | 0.8965±0.0086 | 0.1892±0.0267 | 50.0 |
| seattle_pooled_pairwise | logreg | tabular | 3 | 0.8214±0.0000 | 0.9679±0.0000 | 0.0482±0.0000 | 59.0 |
| seattle_pooled_pairwise | cnn_weighted | regional_raster_cnn | 3 | 0.8131±0.0124 | 0.9626±0.0024 | 0.3028±0.0064 | 59.0 |
| seattle_pooled_pairwise | cnn_focal | regional_raster_cnn | 3 | 0.8119±0.0311 | 0.9607±0.0002 | 0.2944±0.0172 | 59.0 |
| seattle_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | 3 | 0.8090±0.0272 | 0.9607±0.0002 | 0.2340±0.0319 | 59.0 |
| seattle_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | 3 | 0.8082±0.0037 | 0.9626±0.0024 | 0.3198±0.0050 | 59.0 |
| seattle_pooled_pairwise | extra_trees | tabular | 3 | 0.8002±0.0282 | 0.9687±0.0007 | 0.0300±0.0015 | 59.0 |
| seattle_pooled_pairwise | random_forest | tabular | 3 | 0.7884±0.0102 | 0.9570±0.0036 | 0.0228±0.0038 | 59.0 |
| seattle_pooled_pairwise | torch_mlp | tabular | 3 | 0.7753±0.0056 | 0.9438±0.0007 | 0.1792±0.0332 | 59.0 |
| seattle_pooled_pairwise | hgbt | tabular | 3 | 0.7647±0.0000 | 0.9622±0.0000 | 0.0419±0.0000 | 59.0 |
| seattle_pooled_pairwise | rule_score | tabular | 3 | 0.5714±0.0000 | 0.9006±0.0000 | 0.1521±0.0000 | 59.0 |

## Winner Frequency

| Dataset | Model | Family | Wins | Total Seeds | Win Rate |
|---|---|---|---:|---:|---:|
| houston_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | 1 | 3 | 0.3333 |
| houston_pooled_pairwise | hgbt | tabular | 2 | 3 | 0.6667 |
| nola_pooled_pairwise | hgbt | tabular | 3 | 3 | 1.0000 |
| seattle_pooled_pairwise | cnn_focal | regional_raster_cnn | 2 | 3 | 0.6667 |
| seattle_pooled_pairwise | logreg | tabular | 1 | 3 | 0.3333 |

## Recommended Model Per Dataset

| Dataset | Recommended Model | Family | F1 mean±std | ECE mean±std | Candidate Count | Gate Status |
|---|---|---|---:|---:|---:|---|
| houston_pooled_pairwise | hgbt | tabular | 0.8286±0.0000 | 0.0229±0.0000 | 1 | pass_within_f1_band |
| nola_pooled_pairwise | hgbt | tabular | 0.6015±0.0000 | 0.0237±0.0000 | 1 | pass_within_f1_band |
| seattle_pooled_pairwise | logreg | tabular | 0.8214±0.0000 | 0.0482±0.0000 | 3 | pass_within_f1_band |

## Outputs

- run_manifest_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_run_manifest.json`
- raw_rows_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_raw_rows.csv`
- aggregate_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_aggregate.csv`
- winner_rows_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_winner_rows.csv`
- winner_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_winner_summary.csv`
- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_recommendation.csv`
- recommendation_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_recommendation.json`
- recommendation_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_recommendation.md`
- summary_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_summary.md`
