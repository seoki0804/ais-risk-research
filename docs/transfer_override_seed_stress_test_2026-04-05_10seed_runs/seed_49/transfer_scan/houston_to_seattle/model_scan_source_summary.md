# Pairwise Benchmark Summary

## Dataset

- Input: `/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/houston_pooled_pairwise.csv`
- Row count: `2175`
- Positive rate: `0.0680`
- Unique timestamps: `1643`
- Random seed: `49`
- Benchmark elapsed (sec): `0.36105320788919926`

## Split

- Strategy: `own_ship`
- Train rows: `1751`
- Validation rows: `332`
- Test rows: `92`
- Train own ships: `3`
- Validation own ships: `1`
- Test own ships: `1`

## Models

### hgbt

- Threshold: `0.38`
- AUROC: `1.0`
- AUPRC: `1.0`
- F1: `1.0000`
- Precision: `1.0000`
- Recall: `1.0000`
- Elapsed (sec): `0.3153304159641266`

### rule_score

- Threshold: `0.41`
- AUROC: `0.8351648351648352`
- AUPRC: `0.0625`
- F1: `0.1111`
- Precision: `0.0588`
- Recall: `1.0000`
- Elapsed (sec): `0.040592791978269815`
