# Calibration Evaluation Summary

## Inputs

- predictions_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_41/transfer_scan/houston_to_seattle/model_scan_target_predictions.csv`
- models: `hgbt, rule_score`
- bin_count: `10`

## Model Calibration Metrics

| Model | Status | Samples | SkippedRows | Brier | ECE | MCE | MeanScore | PositiveRate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| hgbt | completed | 1503 | 0 | 0.0493 | 0.0428 | 0.5700 | 0.2082 | 0.1763 |
| rule_score | completed | 1503 | 0 | 0.1154 | 0.1399 | 0.2485 | 0.2860 | 0.1763 |

## Outputs

- summary_json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_41/transfer_scan/houston_to_seattle/model_scan_target_calibration_summary.json`
- summary_md: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_41/transfer_scan/houston_to_seattle/model_scan_target_calibration_summary.md`
- calibration_bins_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_41/transfer_scan/houston_to_seattle/model_scan_target_calibration_bins.csv`
- calibration_bin_rows: `20`
