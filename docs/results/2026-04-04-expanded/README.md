# Results Bundle (2026-04-04 Expanded Models)

This bundle captures the expanded all-model run that adds `random_forest` and `extra_trees` to the tabular family and re-runs:

- Multi-area leaderboard (`Houston/NOLA/Seattle`, own-ship split, support-aware auto-adjust)
- Seed sweep aggregation (`seeds=41,42,43`)
- Recommendation outputs with F1-tolerance + ECE tie-break rule

## Key Files

- `all_models_multiarea_leaderboard.csv/.md`
- `all_models_seed_sweep_summary.json/.md`
- `all_models_seed_sweep_aggregate.csv`
- `all_models_seed_sweep_winner_summary.csv`
- `all_models_seed_sweep_recommendation.csv/.json/.md`
- `bundle_manifest_2026-04-04-expanded.txt`

## Quick Takeaway

- Recommended per region remains:
  - Houston: `hgbt`
  - NOLA: `hgbt`
  - Seattle: `logreg`
- Added tree ensembles improve some regional scores but do not change the final recommendation under the current calibration-aware rule.
