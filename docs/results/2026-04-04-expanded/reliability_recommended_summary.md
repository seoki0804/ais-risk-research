# Reliability Summary (Recommended Models)

## Inputs

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_recommendation.csv`
- run_manifest_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_run_manifest.csv`
- num_bins: `10`

## Region Summary

| Region | Dataset | Model | Seed Runs | Samples | Positive Rate | ECE | Brier | Figure |
|---|---|---|---:|---:|---:|---:|---:|---|
| houston | houston_pooled_pairwise | hgbt | 3 | 1272 | 0.0943 | 0.0229 | 0.0238 | `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report/houston_recommended_reliability.png` |
| nola | nola_pooled_pairwise | hgbt | 3 | 4113 | 0.0365 | 0.0237 | 0.0262 | `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report/nola_recommended_reliability.png` |
| seattle | seattle_pooled_pairwise | logreg | 3 | 1263 | 0.1401 | 0.0482 | 0.0518 | `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report/seattle_recommended_reliability.png` |

## Outputs

- region_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report/reliability_recommended_region_summary.csv`
- region_bins_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report/reliability_recommended_bins.csv`
- summary_md: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report/reliability_recommended_summary.md`
- summary_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report/reliability_recommended_summary.json`
