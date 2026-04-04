# True Unseen-Area Evidence Report

## Inputs

- target_model: `hgbt`
- comparator_model: `logreg`
- min_test_positive_support: `10`
- true_area_pairwise_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r5_true_new_area_ny_nj_pooled/ny_nj_pooled_pairwise_summary.json`
- true_area_pairwise_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r13_true_new_area_la_long_beach_pooled/la_long_beach_pooled_pairwise_summary.json`
- true_area_pairwise_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r24_true_new_area_savannah_pooled/savannah_pooled_pairwise_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r36_cross_year_ny_nj_transfer/ny_nj_2023_to_2024_transfer_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r36_cross_year_ny_nj_transfer/ny_nj_2024_to_2023_transfer_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r59_cross_year_seattle_transfer/seattle_2023_to_2024_transfer_summary.json`
- transfer_summary: `/Users/seoki/Desktop/research/outputs/2026-03-17_r59_cross_year_seattle_transfer/seattle_2024_to_2023_transfer_summary.json`

## Pooled True New-Area Benchmark Snapshot

| Region | Split | Rows | Pos rate | Test rows | Test pos | Support | hgbt F1 | logreg F1 | Δ(hgbt-logreg) | hgbt AUROC |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| la_long_beach | own_ship | 853 | 0.1067 | 163 | 3 | low | 0.4000 | 0.1765 | 0.2235 | 0.9833 |
| la_long_beach | timestamp | 853 | 0.1067 | 169 | 26 | ok | 0.8333 | 0.8929 | -0.0595 | 0.9841 |
| ny_nj | own_ship | 960 | 0.0625 | 290 | 6 | low | 0.5333 | 0.0000 | 0.5333 | 0.9437 |
| ny_nj | timestamp | 960 | 0.0625 | 172 | 6 | low | 0.3333 | 0.5000 | -0.1667 | 0.9558 |
| savannah | own_ship | 198 | 0.0051 | 20 | 0 | low | 0.0000 | 0.0000 | 0.0000 | n/a |
| savannah | timestamp | 198 | 0.0051 | 34 | 0 | low | 0.0000 | 0.0000 | 0.0000 | n/a |

## Cross-Year Transfer Snapshot

| Direction | Region | Target rows | Target pos rate | hgbt source F1 | hgbt target F1 | ΔF1(target-source) |
|---|---|---:|---:|---:|---:|---:|
| ny_nj_2023_to_2024 | ny_nj | 1298 | 0.0485 | 0.5333 | 0.6281 | 0.0948 |
| ny_nj_2024_to_2023 | ny_nj | 960 | 0.0625 | 0.6667 | 0.6992 | 0.0325 |
| seattle_2023_to_2024 | seattle | 652 | 0.1534 | 0.7952 | 0.7685 | -0.0267 |
| seattle_2024_to_2023 | seattle | 1503 | 0.1763 | 0.7879 | 0.8191 | 0.0313 |

## Examiner Interpretation

- low-support true-area splits (`test positives < 10`): `5` (la_long_beach:own_ship, ny_nj:own_ship, ny_nj:timestamp, savannah:own_ship, savannah:timestamp)
- own_ship hgbt F1 range: `0.0000 - 0.5333`
- timestamp hgbt F1 range: `0.0000 - 0.8333`
- transfer negative-ΔF1 pairs: `1/4` (seattle_2023_to_2024(-0.0267))

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_detail.csv`
- summary_csv: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv`
- summary_json: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed.json`
