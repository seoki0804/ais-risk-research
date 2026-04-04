# All Models Seed Sweep Summary

## Inputs

- output_root: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed`
- regions: `houston, nola, seattle`
- seeds: `41, 42, 43, 44, 45, 46, 47, 48, 49, 50`
- include_regional_cnn: `True`
- split_strategy: `own_ship`
- auto_adjust_split_for_support: `True`
- min_positive_support: `10`
- recommendation_f1_tolerance: `0.01`
- recommendation_max_ece_mean: `0.1`

## Aggregated Model Metrics

| Dataset | Model | Family | Runs | F1 mean±std (CI95) | AUROC mean±std (CI95) | ECE mean±std (CI95) | Positive mean |
|---|---|---|---:|---:|---:|---:|---:|
| houston_pooled_pairwise | hgbt | tabular | 10 | 0.8286±0.0000 (0.0000) | 0.9833±0.0000 (0.0000) | 0.0229±0.0000 (0.0000) | 40.0 |
| houston_pooled_pairwise | cnn_weighted | regional_raster_cnn | 10 | 0.8197±0.0274 (0.0170) | 0.9907±0.0018 (0.0011) | 0.1674±0.0268 (0.0166) | 40.0 |
| houston_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | 10 | 0.8195±0.0329 (0.0204) | 0.9907±0.0018 (0.0011) | 0.1620±0.0325 (0.0202) | 40.0 |
| houston_pooled_pairwise | extra_trees | tabular | 10 | 0.8135±0.0048 (0.0030) | 0.9764±0.0021 (0.0013) | 0.0348±0.0038 (0.0023) | 40.0 |
| houston_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | 10 | 0.8117±0.0249 (0.0154) | 0.9899±0.0033 (0.0020) | 0.1188±0.0178 (0.0111) | 40.0 |
| houston_pooled_pairwise | cnn_focal | regional_raster_cnn | 10 | 0.8088±0.0328 (0.0203) | 0.9899±0.0033 (0.0020) | 0.2205±0.0274 (0.0170) | 40.0 |
| houston_pooled_pairwise | random_forest | tabular | 10 | 0.8056±0.0053 (0.0033) | 0.9775±0.0011 (0.0007) | 0.0286±0.0013 (0.0008) | 40.0 |
| houston_pooled_pairwise | logreg | tabular | 10 | 0.7317±0.0000 (0.0000) | 0.9564±0.0000 (0.0000) | 0.0716±0.0000 (0.0000) | 40.0 |
| houston_pooled_pairwise | torch_mlp | tabular | 10 | 0.7302±0.0410 (0.0254) | 0.9661±0.0132 (0.0082) | 0.1902±0.0324 (0.0201) | 40.0 |
| houston_pooled_pairwise | rule_score | tabular | 10 | 0.4138±0.0000 (0.0000) | 0.9052±0.0000 (0.0000) | 0.1718±0.0000 (0.0000) | 40.0 |
| nola_pooled_pairwise | hgbt | tabular | 10 | 0.6015±0.0000 (0.0000) | 0.9707±0.0000 (0.0000) | 0.0237±0.0000 (0.0000) | 50.0 |
| nola_pooled_pairwise | random_forest | tabular | 10 | 0.5402±0.0218 (0.0135) | 0.9672±0.0015 (0.0009) | 0.0409±0.0016 (0.0010) | 50.0 |
| nola_pooled_pairwise | extra_trees | tabular | 10 | 0.5162±0.0156 (0.0096) | 0.9542±0.0030 (0.0018) | 0.0581±0.0012 (0.0007) | 50.0 |
| nola_pooled_pairwise | cnn_weighted | regional_raster_cnn | 10 | 0.4456±0.0611 (0.0379) | 0.9620±0.0035 (0.0022) | 0.1106±0.0109 (0.0067) | 50.0 |
| nola_pooled_pairwise | rule_score | tabular | 10 | 0.4455±0.0000 (0.0000) | 0.9735±0.0000 (0.0000) | 0.1412±0.0000 (0.0000) | 50.0 |
| nola_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | 10 | 0.4300±0.0183 (0.0113) | 0.9620±0.0035 (0.0022) | 0.0962±0.0108 (0.0067) | 50.0 |
| nola_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | 10 | 0.4271±0.0114 (0.0071) | 0.9622±0.0039 (0.0024) | 0.0915±0.0137 (0.0085) | 50.0 |
| nola_pooled_pairwise | cnn_focal | regional_raster_cnn | 10 | 0.4264±0.0129 (0.0080) | 0.9622±0.0039 (0.0024) | 0.1913±0.0119 (0.0074) | 50.0 |
| nola_pooled_pairwise | logreg | tabular | 10 | 0.4248±0.0000 (0.0000) | 0.9204±0.0000 (0.0000) | 0.0531±0.0000 (0.0000) | 50.0 |
| nola_pooled_pairwise | torch_mlp | tabular | 10 | 0.4052±0.0475 (0.0294) | 0.8996±0.0324 (0.0201) | 0.2015±0.0206 (0.0127) | 50.0 |
| seattle_pooled_pairwise | logreg | tabular | 10 | 0.8214±0.0000 (0.0000) | 0.9679±0.0000 (0.0000) | 0.0482±0.0000 (0.0000) | 59.0 |
| seattle_pooled_pairwise | extra_trees | tabular | 10 | 0.8174±0.0261 (0.0162) | 0.9643±0.0048 (0.0030) | 0.0300±0.0017 (0.0011) | 59.0 |
| seattle_pooled_pairwise | cnn_weighted | regional_raster_cnn | 10 | 0.8078±0.0088 (0.0055) | 0.9621±0.0036 (0.0022) | 0.3054±0.0293 (0.0181) | 59.0 |
| seattle_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | 10 | 0.8060±0.0206 (0.0127) | 0.9611±0.0033 (0.0021) | 0.2475±0.0303 (0.0188) | 59.0 |
| seattle_pooled_pairwise | cnn_focal | regional_raster_cnn | 10 | 0.8045±0.0240 (0.0149) | 0.9611±0.0033 (0.0021) | 0.3057±0.0203 (0.0126) | 59.0 |
| seattle_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | 10 | 0.7946±0.0202 (0.0125) | 0.9621±0.0036 (0.0022) | 0.3224±0.0260 (0.0161) | 59.0 |
| seattle_pooled_pairwise | random_forest | tabular | 10 | 0.7914±0.0164 (0.0102) | 0.9591±0.0037 (0.0023) | 0.0232±0.0032 (0.0020) | 59.0 |
| seattle_pooled_pairwise | torch_mlp | tabular | 10 | 0.7662±0.0149 (0.0093) | 0.9474±0.0084 (0.0052) | 0.1430±0.0310 (0.0192) | 59.0 |
| seattle_pooled_pairwise | hgbt | tabular | 10 | 0.7647±0.0000 (0.0000) | 0.9622±0.0000 (0.0000) | 0.0419±0.0000 (0.0000) | 59.0 |
| seattle_pooled_pairwise | rule_score | tabular | 10 | 0.5714±0.0000 (0.0000) | 0.9006±0.0000 (0.0000) | 0.1521±0.0000 (0.0000) | 59.0 |

## Winner Frequency

| Dataset | Model | Family | Wins | Total Seeds | Win Rate |
|---|---|---|---:|---:|---:|
| houston_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | 1 | 10 | 0.1000 |
| houston_pooled_pairwise | cnn_weighted | regional_raster_cnn | 1 | 10 | 0.1000 |
| houston_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | 1 | 10 | 0.1000 |
| houston_pooled_pairwise | hgbt | tabular | 7 | 10 | 0.7000 |
| nola_pooled_pairwise | cnn_weighted | regional_raster_cnn | 1 | 10 | 0.1000 |
| nola_pooled_pairwise | hgbt | tabular | 9 | 10 | 0.9000 |
| seattle_pooled_pairwise | cnn_focal | regional_raster_cnn | 2 | 10 | 0.2000 |
| seattle_pooled_pairwise | extra_trees | tabular | 4 | 10 | 0.4000 |
| seattle_pooled_pairwise | logreg | tabular | 4 | 10 | 0.4000 |

## Recommended Model Per Dataset

| Dataset | Recommended Model | Family | F1 mean±std | ECE mean±std | Candidate Count | Gate Status |
|---|---|---|---:|---:|---:|---|
| houston_pooled_pairwise | hgbt | tabular | 0.8286±0.0000 | 0.0229±0.0000 | 3 | pass_within_f1_band |
| nola_pooled_pairwise | hgbt | tabular | 0.6015±0.0000 | 0.0237±0.0000 | 1 | pass_within_f1_band |
| seattle_pooled_pairwise | extra_trees | tabular | 0.8174±0.0261 | 0.0300±0.0017 | 2 | pass_within_f1_band |

## Outputs

- run_manifest_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_run_manifest.json`
- raw_rows_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_raw_rows.csv`
- aggregate_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv`
- winner_rows_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_winner_rows.csv`
- winner_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_winner_summary.csv`
- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- recommendation_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.json`
- recommendation_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.md`
- summary_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_summary.md`
