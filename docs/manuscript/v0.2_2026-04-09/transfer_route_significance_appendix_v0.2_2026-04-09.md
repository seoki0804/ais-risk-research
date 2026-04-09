# Transfer-Route Significance Appendix v0.2 (2026-04-09)

This appendix reports bootstrap-based transfer-route significance using source/target prediction CSV pairs.
Data source: `docs/results/2026-04-04-expanded-10seed` and linked transfer prediction files.

## Test Design
- Unit of analysis: route-level transfer pair (source->target).
- Statistic: delta F1 (target - source) under fixed threshold transfer.
- Bootstrap protocol: stratified bootstrap on source and target prediction sets (n=2000).
- Evidence fields: CI95, two-sided bootstrap p-value vs zero, and direction probability.

## Route-wise Results
| source_region | target_region | recommended_model | observed_delta_f1 | bootstrap_delta_ci95 | bootstrap_p_two_sided | direction_probability | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| houston | nola | hgbt | -0.1383 | [-0.1634, -0.1152] | 0.0000 | 1.0000 | statistically_supported_negative_transfer |
| houston | seattle | hgbt | -0.2103 | [-0.2413, -0.1767] | 0.0000 | 1.0000 | statistically_supported_negative_transfer |
| nola | houston | hgbt | +0.3213 | [+0.2332, +0.3986] | 0.0000 | 1.0000 | statistically_supported_positive_transfer |
| nola | seattle | hgbt | +0.4439 | [+0.3545, +0.5174] | 0.0000 | 1.0000 | statistically_supported_positive_transfer |
| seattle | houston | extra_trees | +0.0021 | [-0.0977, +0.1154] | 0.9670 | 0.5165 | not_conclusive |
| seattle | nola | extra_trees | +0.0488 | [-0.0393, +0.1521] | 0.2960 | 0.8520 | not_conclusive |

## Interpretation Notes
- houston->nola: ΔF1=-0.1383, bootstrap p=0.0000, direction_prob=1.0000
- houston->seattle: ΔF1=-0.2103, bootstrap p=0.0000, direction_prob=1.0000
- nola->houston: ΔF1=+0.3213, bootstrap p=0.0000, direction_prob=1.0000
- nola->seattle: ΔF1=+0.4439, bootstrap p=0.0000, direction_prob=1.0000
- seattle->houston: ΔF1=+0.0021, bootstrap p=0.9670, direction_prob=0.5165
- seattle->nola: ΔF1=+0.0488, bootstrap p=0.2960, direction_prob=0.8520

## Limitations
- This appendix is based on single-run route artifacts and bootstrap resampling.
- Full repeated-randomization (multi-run) transfer significance is still an open next-step item.
