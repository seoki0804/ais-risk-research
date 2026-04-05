# Transfer Calibration Probe

## Inputs

- transfer_scan_detail_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_scan/houston_transfer_model_scan_detail.csv`
- source_region_filter: `houston`
- model_filter: `hgbt, rule_score`
- methods: `none, isotonic`
- threshold_grid_step: `0.0100`
- ece_gate_max: `0.1000`
- max_negative_pairs_allowed: `1`

## Model x Method Summary

| Model | Method | Completed | Neg(Fixed) | Neg(Retuned) | Mean ΔF1 Fixed | Mean ΔF1 Retuned | Max Target ECE | CombinedPass(Fixed/Retuned) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| hgbt | isotonic | 2/2 | 2 | 2 | -0.1765 | -0.1416 | 0.0415 | no/no |
| hgbt | none | 2/2 | 2 | 2 | -0.1743 | -0.1331 | 0.0428 | no/no |
| rule_score | isotonic | 2/2 | 0 | 0 | 0.6032 | 0.6058 | 0.0684 | yes/yes |
| rule_score | none | 2/2 | 0 | 0 | 0.5436 | 0.5942 | 0.1399 | no/no |

## Top Combined-Pass Candidates

- fixed-threshold pass count: `1`
- retuned-threshold pass count: `1`

### Fixed

- `rule_score/isotonic`: mean ΔF1 fixed `0.6032`, max target ECE `0.0684`, negative fixed `0`

### Retuned

- `rule_score/isotonic`: mean ΔF1 retuned `0.6058`, max target ECE `0.0684`, negative retuned `0`

## Outputs

- detail_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_calibration_probe_detail.csv`
- model_method_summary_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_calibration_probe_model_method_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_calibration_probe.md`
- summary_json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_calibration_probe.json`
