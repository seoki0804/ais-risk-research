# Multi-Source Transfer-Model-Scan Summary

- scan_output_root: `/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed`
- source_regions: `houston, nola, seattle`
- max_target_ece: `0.1000`
- max_negative_pairs_allowed: `1`
- recommended_combined_pass_count: `2/3`
- best_combined_pass_count: `2/3`
- recommendation_mismatch_count: `2`

| Source | Recommended | Rec Combined Pass | Rec Neg Pairs | Rec Max ECE | Best Combined | Best Neg Pairs | Best Max ECE |
|---|---|---:|---:|---:|---|---:|---:|
| houston | hgbt | no | 2 | 0.0428 | None | None | n/a |
| nola | hgbt | yes | 0 | 0.0260 | extra_trees | 0 | 0.0534 |
| seattle | random_forest | yes | 0 | 0.0220 | random_forest | 0 | 0.0220 |
