# Calibration Evaluation Summary

## Inputs

- predictions_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_49/transfer_scan/houston_to_nola/model_scan_target_predictions.csv`
- models: `hgbt, rule_score`
- bin_count: `10`

## Model Calibration Metrics

| Model | Status | Samples | SkippedRows | Brier | ECE | MCE | MeanScore | PositiveRate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| hgbt | completed | 2963 | 0 | 0.0307 | 0.0246 | 0.5226 | 0.1337 | 0.1397 |
| rule_score | completed | 2963 | 0 | 0.0779 | 0.1398 | 0.2026 | 0.2249 | 0.1397 |

## Outputs

- summary_json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_49/transfer_scan/houston_to_nola/model_scan_target_calibration_summary.json`
- summary_md: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_49/transfer_scan/houston_to_nola/model_scan_target_calibration_summary.md`
- calibration_bins_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_49/transfer_scan/houston_to_nola/model_scan_target_calibration_bins.csv`
- calibration_bin_rows: `20`
