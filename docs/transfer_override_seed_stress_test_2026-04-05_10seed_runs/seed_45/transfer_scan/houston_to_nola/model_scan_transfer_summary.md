# Transfer Benchmark Summary

## Source / Target Datasets

- Train input: `/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/houston_pooled_pairwise.csv`
- Target input: `/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/nola_pooled_pairwise.csv`
- Source rows: `2175`
- Source positive rate: `0.0680`
- Target rows: `2963`
- Target positive rate: `0.1397`
- Random seed: `45`
- Transfer elapsed (sec): `0.4787172921933234`

## Source Split

- Strategy: `own_ship`
- Train rows: `1751`
- Validation rows: `332`
- Test rows: `92`
- Train own ships: `3`
- Validation own ships: `1`
- Test own ships: `1`

## Models

| Model | Threshold | SourceTestF1 | SourceTestECE? | TargetTransferF1 | TargetTransferAUPRC | ElapsedSec |
|---|---:|---:|---:|---:|---:|---:|
| hgbt | 0.3800 | 1.0000 | n/a | 0.8617 | 0.9340 | 0.4137 |
| rule_score | 0.4100 | 0.1111 | n/a | 0.7268 | 0.7364 | 0.0505 |

## Outputs

- source_summary_json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_scan/houston_to_nola/model_scan_source_summary.json`
- source_summary_md: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_scan/houston_to_nola/model_scan_source_summary.md`
- source_test_predictions_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_scan/houston_to_nola/model_scan_source_test_predictions.csv`
- source_val_predictions_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_scan/houston_to_nola/model_scan_source_val_predictions.csv`
- target_predictions_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_scan/houston_to_nola/model_scan_target_predictions.csv`
- transfer_summary_json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_scan/houston_to_nola/model_scan_transfer_summary.json`
- transfer_summary_md: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs/seed_45/transfer_scan/houston_to_nola/model_scan_transfer_summary.md`
