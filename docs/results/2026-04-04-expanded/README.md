# Results Bundle (2026-04-04 Expanded Models)

This bundle captures the expanded all-model run that adds `random_forest` and `extra_trees` to the tabular family and re-runs:

- Multi-area leaderboard (`Houston/NOLA/Seattle`, own-ship split, support-aware auto-adjust)
- Seed sweep aggregation (`seeds=41,42,43`)
  - includes mean/std and CI95 columns in aggregate table
- Recommendation outputs with F1-tolerance + ECE tie-break rule
- Out-of-time(timestamp split) check for the final recommended model per region
- Cross-region transfer check for source-region recommended models

## Key Files

- `all_models_multiarea_leaderboard.csv/.md`
- `all_models_seed_sweep_summary.json/.md`
- `all_models_seed_sweep_aggregate.csv`
- `all_models_seed_sweep_winner_summary.csv`
- `all_models_seed_sweep_recommendation.csv/.json/.md`
- `out_of_time_recommendation_check.csv/.md`
- `transfer_recommendation_check.csv/.md`
- `bundle_manifest_2026-04-04-expanded.txt`

## Quick Takeaway

- Recommended per region remains:
  - Houston: `hgbt`
  - NOLA: `hgbt`
  - Seattle: `logreg`
- Added tree ensembles improve some regional scores but do not change the final recommendation under the current calibration-aware rule.
- Out-of-time check shows mixed drift:
  - Houston/Seattle F1 decrease
  - NOLA F1 increase
  - Seattle ECE increase to `0.0858` (still below gate `0.10`)
- Cross-region transfer check confirms substantial domain shift in 일부 방향(음수 ΔF1), therefore region-aware 운영이 여전히 필요.
