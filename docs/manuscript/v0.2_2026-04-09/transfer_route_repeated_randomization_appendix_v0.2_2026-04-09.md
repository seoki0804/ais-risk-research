# Transfer-Route Repeated-Randomization Appendix v0.2 (2026-04-09)

This appendix reports repeated-randomization significance for transfer-route delta F1.
Data source: `docs/results/2026-04-04-expanded-10seed` and linked transfer prediction files.

## Test Design
- Unit of analysis: route-level transfer pair (source->target).
- Statistic: delta F1 (target - source) under fixed threshold transfer.
- Repeated-randomization protocol: 25 runs x 800 stratified bootstrap draws per run.
- Reported p-values: run-wise two-sided p summarized by mean/median/max.
- Multiple-comparison control: Holm correction on route-level median p-values.

## Route-wise Results
| source_region | target_region | recommended_model | observed_delta_f1 | randomization_runs | delta_mean_across_runs | delta_ci95_pooled | p_two_sided_median | p_two_sided_median_holm | direction_consistency | significant_runs | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| houston | nola | hgbt | -0.1383 | 25 | -0.1383 | [-0.1630, -0.1149] | 0.0000 | 0.0000 | 1.0000 | 25 | statistically_supported_after_holm |
| houston | seattle | hgbt | -0.2103 | 25 | -0.2103 | [-0.2429, -0.1783] | 0.0000 | 0.0000 | 1.0000 | 25 | statistically_supported_after_holm |
| nola | houston | hgbt | +0.3213 | 25 | +0.3197 | [+0.2316, +0.4027] | 0.0000 | 0.0000 | 1.0000 | 25 | statistically_supported_after_holm |
| nola | seattle | hgbt | +0.4439 | 25 | +0.4420 | [+0.3588, +0.5199] | 0.0000 | 0.0000 | 1.0000 | 25 | statistically_supported_after_holm |
| seattle | houston | extra_trees | +0.0021 | 25 | +0.0020 | [-0.0971, +0.1092] | 0.9750 | 0.9750 | 0.9600 | 0 | not_conclusive_after_holm |
| seattle | nola | extra_trees | +0.0488 | 25 | +0.0488 | [-0.0404, +0.1489] | 0.3100 | 0.6200 | 1.0000 | 0 | not_conclusive_after_holm |

## Interpretation Notes
- houston->nola: median p=0.0000, Holm p=0.0000, direction_consistency=1.0000, sig_runs=25/25
- houston->seattle: median p=0.0000, Holm p=0.0000, direction_consistency=1.0000, sig_runs=25/25
- nola->houston: median p=0.0000, Holm p=0.0000, direction_consistency=1.0000, sig_runs=25/25
- nola->seattle: median p=0.0000, Holm p=0.0000, direction_consistency=1.0000, sig_runs=25/25
- seattle->houston: median p=0.9750, Holm p=0.9750, direction_consistency=0.9600, sig_runs=0/25
- seattle->nola: median p=0.3100, Holm p=0.6200, direction_consistency=1.0000, sig_runs=0/25

## Limitations
- This protocol remains resampling-based and does not replace external-regime validation.
- Route counts are limited by available transfer artifacts in the current release.
