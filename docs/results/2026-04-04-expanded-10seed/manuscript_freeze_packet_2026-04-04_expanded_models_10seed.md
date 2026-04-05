# Manuscript Freeze Packet

## Inputs

- unseen_area_summary_csv: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv`
- threshold_robustness_summary_csv: `/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed_summary.csv`
- significance_csv: `/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed.csv`
- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- aggregate_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv`

## Frozen Claim Text (Paste-Ready)

1. True unseen-area generalization claim is locked to support-governed evidence only: 8/8 evaluated splits satisfy the minimum support policy (test positives >= 10), with low-support count=0 (none).
2. Transfer-scope claim is bounded to the evaluated cross-year independent-harbor set: coverage=3 regions, negative-DeltaF1 pairs=1/6.
3. Operator-threshold policy is locked per region by minimum mean regret over predefined cost profiles (balanced, fn_heavy, fn_very_heavy, fp_heavy). The selected profile and threshold statistics are frozen in the operator-profile lock table.

## Operator Profile Lock Table

| Region | Dataset | Model | Locked Profile | Mean Regret | Mean Rec Th | Mean Best Th |
|---|---|---|---|---:|---:|---:|
| houston | houston_pooled_pairwise | hgbt | balanced | 0.000 | 0.9500 | 0.9500 |
| nola | nola_pooled_pairwise | hgbt | fn_very_heavy | 2.000 | 0.3500 | 0.3000 |
| seattle | seattle_pooled_pairwise | extra_trees | balanced | 1.700 | 0.6050 | 0.5650 |

## Main Result Table Caption Addendum (Paste-Ready)

- Caption addendum: Recommended models show lower calibration error in 3/3 datasets and higher F1 with non-overlapping 95% CI in 1/3 datasets; see significance appendix (/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed.csv).

## Model-Claim Hygiene Freeze

- recommended stable claims: `3/3`
- appendix-only model rows: `16`
- recommended_claim_hygiene_ready: `True`
- caveat sentence: Reviewer caveat: Main-text model claims are restricted to recommended models that satisfy calibration (ECE<=0.10) and seed-variance (F1 std<=0.03) gates; models failing either gate are retained in appendix-only ablation tables.
- model_claim_scope_csv: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed_model_claim_scope.csv`

## Outputs

- summary_md: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.md`
- summary_json: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json`
- operator_profile_lock_csv: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed_operator_profile_lock.csv`
- model_claim_scope_csv: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed_model_claim_scope.csv`
