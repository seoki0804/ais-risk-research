# Transfer Gap Diagnostics

## Inputs

- transfer_check_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv`
- threshold_grid_step: `0.01`
- bootstrap_samples: `500`
- random_seed: `42`

## Summary

- completed pairs: `6/6`
- negative ΔF1 pairs: `2`
- negative ΔF1 pairs with CI upper<0: `0`
- pairs with target retune gain >=0.05 F1: `2`
- max target retune gain pair: `nola->houston:hgbt` (`0.1055`)

## Detail Snapshot

| Source | Target | Model | ΔF1 fixed-th | CI95 low/high | Target retune gain | Target best th |
|---|---|---|---:|---:|---:|---:|
| houston | nola | hgbt | -0.1383 | -0.1631/0.8807 | 0.0032 | 0.4500 |
| houston | seattle | hgbt | -0.2103 | -0.2479/0.8162 | 0.0793 | 0.9400 |
| nola | houston | hgbt | 0.3213 | 0.1842/0.4764 | 0.1055 | 0.6200 |
| nola | seattle | hgbt | 0.4439 | 0.3089/0.5963 | 0.0178 | 0.4200 |
| seattle | houston | extra_trees | 0.0021 | -0.1068/0.1153 | 0.0028 | 0.4700 |
| seattle | nola | extra_trees | 0.0488 | -0.0488/0.1422 | 0.0066 | 0.4400 |

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics_detail.csv`
- summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics.json`
