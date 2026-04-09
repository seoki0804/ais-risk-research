# Out-of-Domain Validation Appendix v0.2 (2026-04-09)

This appendix expands robustness evidence with true-unseen-area and cross-year transfer slices.
Detail source path: `docs/results/2026-04-04-expanded-10seed/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_detail.csv`
Summary source path: `docs/results/2026-04-04-expanded-10seed/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv`
Source summary snapshot: `true_area_row_count=8, transfer_row_count=6, true_area_low_support_count=0`

## Aggregated Summary
| evidence_type | split | row_count | region_count | hgbt_f1_mean | hgbt_f1_min | hgbt_f1_max | hgbt_minus_logreg_f1_mean | negative_delta_count | support_low_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross_year_transfer | own_ship | 6 | 3 | 0.7479 | 0.6281 | 0.8830 | +0.1378 | 1 | 0 |
| true_unseen_area | own_ship | 4 | 4 | 0.7293 | 0.6667 | 0.7789 | +0.1460 | 0 | 0 |
| true_unseen_area | timestamp | 4 | 4 | 0.6357 | 0.3333 | 0.8462 | -0.0521 | 0 | 0 |

## Row-Level Detail
| evidence_type | region | split | direction | hgbt_f1 | hgbt_f1_ci95 | hgbt_minus_logreg_f1 | hgbt_delta_f1 | test_positive_support_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross_year_transfer | la_long_beach | own_ship | la_long_beach_2023_to_2024 | 0.6897 | [0.5660, 0.8067] | +0.3299 | +0.1442 | n/a |
| cross_year_transfer | la_long_beach | own_ship | la_long_beach_2024_to_2023 | 0.8830 | [0.8302, 0.9252] | +0.3940 | +0.4385 | n/a |
| cross_year_transfer | ny_nj | own_ship | ny_nj_2023_to_2024 | 0.6281 | [0.5310, 0.7143] | +0.0781 | +0.0948 | n/a |
| cross_year_transfer | ny_nj | own_ship | ny_nj_2024_to_2023 | 0.6992 | [0.6113, 0.7833] | +0.0572 | +0.0325 | n/a |
| cross_year_transfer | seattle | own_ship | seattle_2023_to_2024 | 0.7685 | [0.7136, 0.8313] | -0.0295 | -0.0267 | n/a |
| cross_year_transfer | seattle | own_ship | seattle_2024_to_2023 | 0.8191 | [0.7858, 0.8503] | -0.0029 | +0.0313 | n/a |
| true_unseen_area | la_long_beach_2023_expanded | own_ship |  | 0.7216 | [0.6145, 0.8219] | +0.0810 | n/a | ok |
| true_unseen_area | la_long_beach_2023_expanded | timestamp |  | 0.8369 | [0.7686, 0.9000] | +0.0148 | n/a | ok |
| true_unseen_area | ny_nj_2023_extended | own_ship |  | 0.7789 | [0.7532, 0.8057] | +0.0107 | n/a | ok |
| true_unseen_area | ny_nj_2023_extended | timestamp |  | 0.8462 | [0.8272, 0.8661] | +0.0087 | n/a | ok |
| true_unseen_area | ny_nj_2024 | own_ship |  | 0.6667 | [0.4478, 0.8387] | +0.2303 | n/a | ok |
| true_unseen_area | ny_nj_2024 | timestamp |  | 0.3333 | [0.0930, 0.5600] | -0.1429 | n/a | ok |
| true_unseen_area | savannah_ownship_focus_augmented | own_ship |  | 0.7500 | [0.5600, 0.9091] | +0.2622 | n/a | ok |
| true_unseen_area | savannah_ownship_focus_augmented | timestamp |  | 0.5263 | [0.3125, 0.6989] | -0.0891 | n/a | ok |

## Interpretation Notes
- cross_year_transfer / own_ship: mean F1=0.7479, mean model gap=+0.1378, negative Δ count=1, low-support=0
- true_unseen_area / own_ship: mean F1=0.7293, mean model gap=+0.1460, negative Δ count=0, low-support=0
- true_unseen_area / timestamp: mean F1=0.6357, mean model gap=-0.0521, negative Δ count=0, low-support=0

## Limitations
- This appendix depends on currently available true-unseen/cross-year artifacts.
- Additional external regimes are still needed for stronger global validity claims.
