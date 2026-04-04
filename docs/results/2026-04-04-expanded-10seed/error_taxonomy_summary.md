# Error Taxonomy (Recommended Models)

## Region Summary

| Region | Dataset | Model | Seed | Samples | FP | FN | FP Rate | FN Rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| houston | houston_pooled_pairwise | hgbt | 42 | 424 | 1 | 11 | 0.0026 | 0.2750 |
| nola | nola_pooled_pairwise | hgbt | 42 | 1371 | 43 | 10 | 0.0326 | 0.2000 |
| seattle | seattle_pooled_pairwise | extra_trees | 42 | 421 | 5 | 15 | 0.0138 | 0.2542 |

## Top Error Patterns (per region, FP/FN, top 5)

### houston FP

| Dimension | Value | Count | Share |
|---|---|---:|---:|
| distance_bucket | <0.5nm | 1 | 1.0000 |
| encounter_type | diverging | 1 | 1.0000 |
| own_vessel_type | tug | 1 | 1.0000 |
| target_vessel_type | cargo | 1 | 1.0000 |
| tcpa_bucket | <0min | 1 | 1.0000 |

### houston FN

| Dimension | Value | Count | Share |
|---|---|---:|---:|
| own_vessel_type | tug | 11 | 1.0000 |
| encounter_type | diverging | 8 | 0.7273 |
| target_vessel_type | tug | 8 | 0.7273 |
| distance_bucket | <0.5nm | 5 | 0.4545 |
| tcpa_bucket | 0-5min | 5 | 0.4545 |

### nola FP

| Dimension | Value | Count | Share |
|---|---|---:|---:|
| encounter_type | diverging | 31 | 0.7209 |
| own_vessel_type | tug | 29 | 0.6744 |
| tcpa_bucket | 0-5min | 25 | 0.5814 |
| distance_bucket | 0.5-1.0nm | 24 | 0.5581 |
| target_vessel_type | passenger | 22 | 0.5116 |

### nola FN

| Dimension | Value | Count | Share |
|---|---|---:|---:|
| own_vessel_type | service | 8 | 0.8000 |
| tcpa_bucket | 10-20min | 7 | 0.7000 |
| encounter_type | crossing | 6 | 0.6000 |
| distance_bucket | 2.0-5.0nm | 5 | 0.5000 |
| distance_bucket | 1.0-2.0nm | 4 | 0.4000 |

### seattle FP

| Dimension | Value | Count | Share |
|---|---|---:|---:|
| own_vessel_type | passenger | 5 | 1.0000 |
| target_vessel_type | passenger | 5 | 1.0000 |
| encounter_type | crossing | 3 | 0.6000 |
| distance_bucket | <0.5nm | 2 | 0.4000 |
| encounter_type | diverging | 2 | 0.4000 |

### seattle FN

| Dimension | Value | Count | Share |
|---|---|---:|---:|
| own_vessel_type | passenger | 15 | 1.0000 |
| target_vessel_type | passenger | 10 | 0.6667 |
| tcpa_bucket | 0-5min | 8 | 0.5333 |
| distance_bucket | 2.0-5.0nm | 6 | 0.4000 |
| encounter_type | crossing | 6 | 0.4000 |

## Outputs

- summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_error_taxonomy_10seed/error_taxonomy_region_summary.csv`
- taxonomy_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_error_taxonomy_10seed/error_taxonomy_details.csv`
- summary_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_error_taxonomy_10seed/error_taxonomy_summary.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_error_taxonomy_10seed/error_taxonomy_summary.json`
