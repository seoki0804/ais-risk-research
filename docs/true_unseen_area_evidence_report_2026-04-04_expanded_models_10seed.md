# True Unseen-Area Evidence Report

## Inputs

- target_model: `hgbt`
- comparator_model: `logreg`
- min_test_positive_support: `10`
- true_area_pairwise_summary: `/Users/seoki/Desktop/research/outputs/2026-04-05_r22_nynj_ext_overridepool_true_new_area_ny_nj_2023_extended_pooled/ny_nj_2023_extended_pooled_pairwise_summary.json`
- true_area_pairwise_summary: `/Users/seoki/Desktop/research/outputs/2026-04-05_r14_true_new_area_la_long_beach_2023_expanded_pooled/la_long_beach_2023_expanded_pooled_pairwise_summary.json`
- true_area_pairwise_summary: `/Users/seoki/Desktop/research/outputs/2026-04-05_r27_true_new_area_savannah_ownship_focus_augmented_pooled/savannah_ownship_focus_augmented_pooled_pairwise_summary.json`
- true_area_pairwise_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r35_cross_year_2024_ny_nj_pooled/ny_nj_2024_pooled_pairwise_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r36_cross_year_ny_nj_transfer/ny_nj_2023_to_2024_transfer_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r36_cross_year_ny_nj_transfer/ny_nj_2024_to_2023_transfer_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r59_cross_year_seattle_transfer/seattle_2023_to_2024_transfer_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r59_cross_year_seattle_transfer/seattle_2024_to_2023_transfer_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-04-05_r2_cross_year_la_long_beach_transfer/la_long_beach_2023_to_2024_transfer_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-04-05_r2_cross_year_la_long_beach_transfer/la_long_beach_2024_to_2023_transfer_summary.json`

## Pooled True New-Area Benchmark Snapshot

| Region | Split | Rows | Pos rate | Test rows | Test pos | Support | hgbt F1 | logreg F1 | Δ(hgbt-logreg) | hgbt AUROC |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| la_long_beach_2023_expanded | own_ship | 4609 | 0.1011 | 1040 | 53 | ok | 0.7216 | 0.6406 | 0.0810 | 0.9749 |
| la_long_beach_2023_expanded | timestamp | 4609 | 0.1011 | 1051 | 74 | ok | 0.8369 | 0.8221 | 0.0148 | 0.9870 |
| ny_nj_2023_extended | own_ship | 25802 | 0.1302 | 5566 | 698 | ok | 0.7789 | 0.7682 | 0.0107 | 0.9606 |
| ny_nj_2023_extended | timestamp | 25802 | 0.1302 | 5016 | 724 | ok | 0.8462 | 0.8375 | 0.0087 | 0.9736 |
| ny_nj_2024 | own_ship | 1298 | 0.0485 | 259 | 15 | ok | 0.6667 | 0.4364 | 0.2303 | 0.9735 |
| ny_nj_2024 | timestamp | 1298 | 0.0485 | 263 | 15 | ok | 0.3333 | 0.4762 | -0.1429 | 0.9578 |
| savannah_ownship_focus_augmented | own_ship | 476 | 0.1555 | 71 | 11 | ok | 0.7500 | 0.4878 | 0.2622 | 0.9803 |
| savannah_ownship_focus_augmented | timestamp | 476 | 0.1555 | 90 | 23 | ok | 0.5263 | 0.6154 | -0.0891 | 0.9299 |

## Cross-Year Transfer Snapshot

| Direction | Region | Target rows | Target pos rate | hgbt source F1 | hgbt target F1 | ΔF1(target-source) |
|---|---|---:|---:|---:|---:|---:|
| la_long_beach_2023_to_2024 | la_long_beach | 494 | 0.0547 | 0.5455 | 0.6897 | 0.1442 |
| la_long_beach_2024_to_2023 | la_long_beach | 853 | 0.1067 | 0.4444 | 0.8830 | 0.4385 |
| ny_nj_2023_to_2024 | ny_nj | 1298 | 0.0485 | 0.5333 | 0.6281 | 0.0948 |
| ny_nj_2024_to_2023 | ny_nj | 960 | 0.0625 | 0.6667 | 0.6992 | 0.0325 |
| seattle_2023_to_2024 | seattle | 652 | 0.1534 | 0.7952 | 0.7685 | -0.0267 |
| seattle_2024_to_2023 | seattle | 1503 | 0.1763 | 0.7879 | 0.8191 | 0.0313 |

## Examiner Interpretation

- low-support true-area splits (`test positives < 10`): `0` (none)
- own_ship hgbt F1 range: `0.6667 - 0.7789`
- timestamp hgbt F1 range: `0.3333 - 0.8462`
- transfer negative-ΔF1 pairs: `1/6` (seattle_2023_to_2024(-0.0267))
- transfer harbor coverage (regions): `3`

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_detail.csv`
- summary_csv: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv`
- summary_json: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed.json`
