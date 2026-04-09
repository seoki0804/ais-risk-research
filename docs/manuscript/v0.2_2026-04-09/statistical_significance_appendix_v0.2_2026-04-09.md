# Statistical Significance Appendix v0.2 (2026-04-09)

This appendix reports seed-matched statistical tests for tabular vs raster-CNN comparisons.
Data source: `docs/results/2026-04-04-expanded-10seed` (raw seed rows resolved from `all_models_seed_sweep_summary.json`).

## Test Design
- Unit of analysis: seed-matched paired metric values by region.
- Metrics: F1 and ECE (delta = tabular - raster-CNN).
- Primary test: exact paired permutation test.
- Secondary test: exact sign test (two-sided).
- Multiple-comparison control: Holm correction across regions (per metric family).

## Region-wise Results
| region | tabular_model | raster_cnn_model | n_pairs | f1_delta_mean_tabular_minus_cnn | f1_permutation_p_holm | ece_delta_mean_tabular_minus_cnn | ece_permutation_p_holm | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| houston | hgbt | cnn_weighted | 10 | +0.0089 | 0.3359 | -0.1446 | 0.0060 | no significant F1 difference; tabular significantly lower ECE |
| nola | hgbt | cnn_weighted | 10 | +0.1559 | 0.0117 | -0.0870 | 0.0060 | tabular significantly higher F1; tabular significantly lower ECE |
| seattle | logreg | cnn_weighted | 10 | +0.0136 | 0.0117 | -0.2572 | 0.0060 | tabular significantly higher F1; tabular significantly lower ECE |

## Interpretation Notes
- houston: ΔF1=+0.0089 (Holm p=0.3359), ΔECE=-0.1446 (Holm p=0.0060)
- nola: ΔF1=+0.1559 (Holm p=0.0117), ΔECE=-0.0870 (Holm p=0.0060)
- seattle: ΔF1=+0.0136 (Holm p=0.0117), ΔECE=-0.2572 (Holm p=0.0060)

## Limitations
- Region-level sample size is limited to 10 seeds.
- Transfer-route significance remains CI-based in the current manuscript; route-level repeated randomization is a next-step item.
