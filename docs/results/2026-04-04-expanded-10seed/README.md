# Results Bundle (2026-04-04 Expanded Models, 10-Seed)

This bundle captures the 10-seed expanded all-model run and its downstream checks:

- Multi-area leaderboard (`Houston/NOLA/Seattle`, own-ship split, support-aware auto-adjust)
- Seed sweep aggregation (`seeds=41..50`)
  - includes mean/std and CI95 columns in aggregate table
- Recommendation outputs with F1-tolerance + ECE hard-gate rule (`ECE<=0.10`)
- Out-of-time(timestamp split) check for the final recommended model per region
- Cross-region transfer check for source-region recommended models
- Reliability diagrams and bin tables for final recommended models
- FP/FN error taxonomy summary/detail for final recommended models
- True unseen-area + cross-year transfer consolidated evidence report
- Reproducibility manifest with SHA256/input-hash/command-log provenance

## Key Files

- `all_models_multiarea_leaderboard.csv/.md`
- `all_models_seed_sweep_summary.json/.md`
- `all_models_seed_sweep_aggregate.csv`
- `all_models_seed_sweep_winner_summary.csv`
- `all_models_seed_sweep_recommendation.csv/.json/.md`
- `out_of_time_recommendation_check.csv/.md`
- `transfer_recommendation_check.csv/.md`
- `reliability_recommended_region_summary.csv`
- `reliability_recommended_bins.csv`
- `reliability_recommended_summary.md/.json`
- `houston_recommended_reliability.png`
- `nola_recommended_reliability.png`
- `seattle_recommended_reliability.png`
- `error_taxonomy_region_summary.csv`
- `error_taxonomy_details.csv`
- `error_taxonomy_summary.md/.json`
- `true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed.md/.json`
- `true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_detail.csv`
- `true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv`
- `(optional) la_long_beach_2024_pooled_pairwise_summary.json`
- `(optional) la_long_beach_2023_to_2024_transfer_summary.json`
- `(optional) la_long_beach_2024_to_2023_transfer_summary.json`
- `external_validity_command_log_2026-04-04_10seed.txt`
- `bundle_manifest_2026-04-04-expanded-10seed.txt`
- `bundle_manifest_2026-04-04-expanded-10seed.json`

## Quick Takeaway

- Recommended per region (10-seed):
  - Houston: `hgbt`
  - NOLA: `hgbt`
  - Seattle: `extra_trees`
- Compared to 3-seed recommendation, Seattle changed `logreg -> extra_trees`.
- Out-of-time check:
  - Houston: F1 decrease (`-0.1013`)
  - NOLA: F1 increase (`+0.2318`)
  - Seattle(extra_trees): small F1 decrease (`-0.0099`) and ECE increase (`+0.0088`, still below `0.10`)
- Reliability summary:
  - Houston(hgbt) ECE `0.0229`
  - NOLA(hgbt) ECE `0.0237`
  - Seattle(extra_trees) ECE `0.0282`
