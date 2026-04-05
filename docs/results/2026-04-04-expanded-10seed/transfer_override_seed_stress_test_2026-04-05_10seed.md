# Transfer Override Seed Stress Test

## Configuration

- input_dir: `/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix`
- source_region: `houston`
- target_regions: `nola, seattle`
- baseline_model/method: `hgbt/none`
- override_model/method: `rule_score/isotonic`
- seeds: `41, 42, 43, 44, 45, 46, 47, 48, 49, 50`
- threshold_grid_step: `0.0100`
- ece_gate_max: `0.1000`
- max_negative_pairs_allowed: `1`

## Headline

- completed seeds: `10/10`
- baseline combined-pass(fixed): `0/10`
- override combined-pass(fixed): `10/10`
- override better negative-pair count: `10/10`
- override better transfer-gate count: `10/10`
- mean source F1 loss (override-baseline): `0.9000`
- max source F1 loss (override-baseline): `0.9000`
- mean target F1 gain (override-baseline): `-0.1225`
- max override target ECE across seeds: `0.0684`
- DQ-3 acceptance met: `True`

## Per-Seed Summary

| Seed | Status | Baseline Neg | Override Neg | Baseline Pass | Override Pass | Source F1 Loss | Target F1 Gain |
|---:|---|---:|---:|---|---|---:|---:|
| 41 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 42 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 43 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 44 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 45 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 46 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 47 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 48 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 49 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |
| 50 | completed | 2 | 0 | fail | pass | 0.9000 | -0.1225 |

## Outputs

- summary_md: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed.md`
- summary_json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed.json`
- per_seed_csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_per_seed.csv`
- run_root: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_runs`
