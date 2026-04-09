# Threshold Utility Appendix v0.2 (2026-04-09)

This appendix evaluates operating-threshold tradeoffs under a miss-sensitive profile.
Cost profile: FN weight = 5, FP weight = 1 (normalized per-region).

## Operating-Point Summary
| region | model_name | governed_threshold | utility_opt_threshold | threshold_shift | governed_f1 | opt_f1 | cost_reduction_pct | governed_fp | governed_fn | opt_fp | opt_fn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| houston | hgbt | 0.95 | 0.05 | -0.90 | 0.8286 | 0.8372 | +46.43 | 1 | 11 | 10 | 4 |
| nola | hgbt | 0.35 | 0.38 | +0.03 | 0.6015 | 0.6250 | +5.38 | 43 | 10 | 38 | 10 |
| seattle | extra_trees | 0.60 | 0.36 | -0.24 | 0.8148 | 0.8308 | +47.50 | 5 | 15 | 17 | 5 |

## Region Interpretation
- houston: governed=0.95 -> utility-opt=0.05, cost_reduction=+46.43%, F1_delta=+0.0086
- nola: governed=0.35 -> utility-opt=0.38, cost_reduction=+5.38%, F1_delta=+0.0235
- seattle: governed=0.60 -> utility-opt=0.36, cost_reduction=+47.50%, F1_delta=+0.0160

## Figure Link
- Utility curve: `figure_4_threshold_utility_curve.svg`

## Limitations
- Cost profile weights are policy assumptions and should be adapted to stakeholder risk preference.
- Utility analysis is based on current recommendation models and available prediction artifacts.
