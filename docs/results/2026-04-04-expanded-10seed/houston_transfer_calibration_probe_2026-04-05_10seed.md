# Transfer Calibration Probe

## Inputs

- transfer_scan_detail_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan_detail.csv`
- source_region_filter: `houston`
- model_filter: `extra_trees, hgbt, logreg, random_forest, rule_score, torch_mlp`
- methods: `none, platt, isotonic`
- threshold_grid_step: `0.0100`
- ece_gate_max: `0.1000`
- max_negative_pairs_allowed: `1`

## Model x Method Summary

| Model | Method | Completed | Neg(Fixed) | Neg(Retuned) | Mean ΔF1 Fixed | Mean ΔF1 Retuned | Max Target ECE | CombinedPass(Fixed/Retuned) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| extra_trees | isotonic | 2/2 | 2 | 2 | -0.1582 | -0.1282 | 0.0616 | no/no |
| extra_trees | none | 2/2 | 2 | 2 | -0.1754 | -0.1277 | 0.0887 | no/no |
| extra_trees | platt | 2/2 | 2 | 2 | -0.1569 | -0.1286 | 0.2003 | no/no |
| hgbt | isotonic | 2/2 | 2 | 2 | -0.1765 | -0.1416 | 0.0415 | no/no |
| hgbt | none | 2/2 | 2 | 2 | -0.1743 | -0.1331 | 0.0428 | no/no |
| hgbt | platt | 2/2 | 2 | 2 | -0.1748 | -0.1325 | 0.1325 | no/no |
| logreg | isotonic | 2/2 | 2 | 2 | -0.2309 | -0.1907 | 0.1371 | no/no |
| logreg | none | 2/2 | 2 | 2 | -0.2309 | -0.1945 | 0.2145 | no/no |
| logreg | platt | 2/2 | 2 | 2 | -0.2271 | -0.2096 | 0.2770 | no/no |
| random_forest | isotonic | 2/2 | 2 | 2 | -0.2079 | -0.1255 | 0.0748 | no/no |
| random_forest | none | 2/2 | 2 | 2 | -0.2049 | -0.1155 | 0.0721 | no/no |
| random_forest | platt | 2/2 | 2 | 2 | -0.2055 | -0.1164 | 0.1890 | no/no |
| rule_score | isotonic | 2/2 | 0 | 0 | 0.6032 | 0.6058 | 0.0684 | yes/yes |
| rule_score | none | 2/2 | 0 | 0 | 0.5436 | 0.5942 | 0.1399 | no/no |
| rule_score | platt | 2/2 | 0 | 0 | 0.5986 | 0.6067 | 0.2412 | no/no |
| torch_mlp | isotonic | 2/2 | 2 | 2 | -0.1785 | -0.1542 | 0.0486 | no/no |
| torch_mlp | none | 2/2 | 2 | 2 | -0.1763 | -0.1498 | 0.2302 | no/no |
| torch_mlp | platt | 2/2 | 2 | 2 | -0.1760 | -0.1502 | 0.1596 | no/no |

## Top Combined-Pass Candidates

- fixed-threshold pass count: `1`
- retuned-threshold pass count: `1`

### Fixed

- `rule_score/isotonic`: mean ΔF1 fixed `0.6032`, max target ECE `0.0684`, negative fixed `0`

### Retuned

- `rule_score/isotonic`: mean ΔF1 retuned `0.6058`, max target ECE `0.0684`, negative retuned `0`

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/docs/houston_transfer_calibration_probe_2026-04-05_10seed_detail.csv`
- model_method_summary_csv: `/Users/seoki/Desktop/research/docs/houston_transfer_calibration_probe_2026-04-05_10seed_model_method_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/docs/houston_transfer_calibration_probe_2026-04-05_10seed.md`
- summary_json: `/Users/seoki/Desktop/research/docs/houston_transfer_calibration_probe_2026-04-05_10seed.json`
