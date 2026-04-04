# Reviewer Quality Audit (10-Seed Expanded Models)

## Scope

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- aggregate_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv`
- winner_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_winner_summary.csv`
- out_of_time_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_out_of_time_check_10seed/out_of_time_recommendation_check.csv`
- transfer_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv`
- reliability_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/reliability_recommended_region_summary.csv`
- taxonomy_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_error_taxonomy_10seed/error_taxonomy_region_summary.csv`

## Recommendation Snapshot

| Region | Dataset | Model | Family | F1 mean±std | ECE mean±std | Gate |
|---|---|---|---|---:|---:|---|
| houston | houston_pooled_pairwise | hgbt | tabular | 0.8286±0.0000 | 0.0229±0.0000 | pass_within_f1_band |
| nola | nola_pooled_pairwise | hgbt | tabular | 0.6015±0.0000 | 0.0237±0.0000 | pass_within_f1_band |
| seattle | seattle_pooled_pairwise | extra_trees | tabular | 0.8174±0.0261 | 0.0300±0.0017 | pass_within_f1_band |

## Examiner Findings

1. Calibration governance is active.
Calibration gate enabled for all regions: `True` (threshold=`0.1000`)

2. Out-of-time drift remains region-dependent.
- negative-ΔF1 regions: `2`
- houston: model `hgbt`, ΔF1 `-0.1013`, ΔECE `0.0012`
- seattle: model `extra_trees`, ΔF1 `-0.0099`, ΔECE `0.0088`

3. Cross-region transfer still shows substantial degradation on multiple directions.
- negative transfer pairs: `3` / `6`
- houston -> seattle: `hgbt` ΔF1 `-0.2007`
- houston -> nola: `hgbt` ΔF1 `-0.1383`
- seattle -> houston: `extra_trees` ΔF1 `-0.0309`

4. Seed variance outliers are concentrated in neural/CNN candidates.
- high variance candidates (F1 std>=0.03): `5`
- nola_pooled_pairwise / cnn_weighted: F1 std `0.0611`, ECE mean `0.1106`
- nola_pooled_pairwise / torch_mlp: F1 std `0.0475`, ECE mean `0.2015`
- houston_pooled_pairwise / torch_mlp: F1 std `0.0410`, ECE mean `0.1902`
- houston_pooled_pairwise / cnn_weighted_temp: F1 std `0.0329`, ECE mean `0.1620`
- houston_pooled_pairwise / cnn_focal: F1 std `0.0328`, ECE mean `0.2205`

5. Error taxonomy indicates region-specific FN pressure that should be addressed in discussion.

| Region | Positive Support (approx) | FP | FN |
|---|---:|---:|---:|
| houston | 400 | 1 | 11 |
| nola | 500 | 43 | 10 |
| seattle | 590 | 5 | 15 |

## Priority TODO (Examiner View)

1. Add true unseen-area evidence (outside current same-ecosystem region set).
2. Add threshold-policy robustness table under operator cost scenarios (FP-heavy vs FN-heavy).
3. Add significance notes for top-model deltas (bootstrap CI or paired test) in main table.

## Top-3 Models Per Dataset (10-seed aggregate)

### houston_pooled_pairwise

| Model | F1 mean±std (CI95) | ECE mean±std |
|---|---:|---:|
| hgbt | 0.8286±0.0000 (0.0000) | 0.0229±0.0000 |
| cnn_weighted | 0.8197±0.0274 (0.0170) | 0.1674±0.0268 |
| cnn_weighted_temp | 0.8195±0.0329 (0.0204) | 0.1620±0.0325 |

### nola_pooled_pairwise

| Model | F1 mean±std (CI95) | ECE mean±std |
|---|---:|---:|
| hgbt | 0.6015±0.0000 (0.0000) | 0.0237±0.0000 |
| random_forest | 0.5402±0.0218 (0.0135) | 0.0409±0.0016 |
| extra_trees | 0.5162±0.0156 (0.0096) | 0.0581±0.0012 |

### seattle_pooled_pairwise

| Model | F1 mean±std (CI95) | ECE mean±std |
|---|---:|---:|
| logreg | 0.8214±0.0000 (0.0000) | 0.0482±0.0000 |
| extra_trees | 0.8174±0.0261 (0.0162) | 0.0300±0.0017 |
| cnn_weighted | 0.8078±0.0088 (0.0055) | 0.3054±0.0293 |

