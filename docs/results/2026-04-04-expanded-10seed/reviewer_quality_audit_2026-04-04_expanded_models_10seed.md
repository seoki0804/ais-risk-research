# Reviewer Quality Audit (10-Seed Expanded Models)

## Scope

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- aggregate_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv`
- winner_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_winner_summary.csv`
- out_of_time_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_out_of_time_check_10seed/out_of_time_recommendation_check.csv`
- transfer_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv`
- reliability_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/reliability_recommended_region_summary.csv`
- taxonomy_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_error_taxonomy_10seed/error_taxonomy_region_summary.csv`
- unseen_area_summary_csv: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv`
- manuscript_freeze_packet_json: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json`
- transfer_model_scan_json: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan.json`
- transfer_gap_summary_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics_summary.csv`
- temporal_robust_summary_json: `/Users/seoki/Desktop/research/docs/temporal_robust_recommendation_2026-04-05_houston_10seed.json`
- out_of_time_threshold_policy_compare_json: `/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.json`
- transfer_policy_governance_lock_json: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed.json`
- transfer_policy_compare_json: `/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_2026-04-05_10seed.json`
- transfer_policy_compare_all_models_json: `/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_all_models_2026-04-05_10seed.json`
- transfer_calibration_probe_json: `/Users/seoki/Desktop/research/docs/houston_transfer_calibration_probe_2026-04-05_10seed.json`
- external_validity_manuscript_assets_json: `/Users/seoki/Desktop/research/docs/external_validity_manuscript_assets_2026-04-05_10seed.json`
- multisource_transfer_model_scan_summary_json: `/Users/seoki/Desktop/research/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed.json`
- multisource_transfer_governance_bridge_json: `/Users/seoki/Desktop/research/docs/multisource_transfer_governance_bridge_2026-04-05_10seed.json`
- data_algorithm_quality_review_json: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed.json`

## Recommendation Snapshot

| Region | Dataset | Model | Family | F1 mean±std | ECE mean±std | Gate |
|---|---|---|---|---:|---:|---|
| houston | houston_pooled_pairwise | hgbt | tabular | 0.8286±0.0000 | 0.0229±0.0000 | pass_within_f1_band |
| nola | nola_pooled_pairwise | hgbt | tabular | 0.6015±0.0000 | 0.0237±0.0000 | pass_within_f1_band |
| seattle | seattle_pooled_pairwise | extra_trees | tabular | 0.8174±0.0261 | 0.0300±0.0017 | pass_within_f1_band |

## Examiner Findings

1. Calibration governance is active.
Calibration gate enabled for all regions: `True` (threshold=`0.1000`)

2. Out-of-time drift remains region-dependent.
- negative-ΔF1 regions: `2`
- houston: model `hgbt`, ΔF1 `-0.1013`, ΔECE `0.0012`
- seattle: model `extra_trees`, ΔF1 `-0.0099`, ΔECE `0.0088`

3. Cross-region transfer still shows substantial degradation on multiple directions.
- negative transfer pairs: `2` / `6`
- houston -> seattle: `hgbt` ΔF1 `-0.2103`
- houston -> nola: `hgbt` ΔF1 `-0.1383`

4. Seed variance outliers are concentrated in neural/CNN candidates.
- high variance candidates (F1 std>=0.03): `5`
- nola_pooled_pairwise / cnn_weighted: F1 std `0.0611`, ECE mean `0.1106`
- nola_pooled_pairwise / torch_mlp: F1 std `0.0475`, ECE mean `0.2015`
- houston_pooled_pairwise / torch_mlp: F1 std `0.0410`, ECE mean `0.1902`
- houston_pooled_pairwise / cnn_weighted_temp: F1 std `0.0329`, ECE mean `0.1620`
- houston_pooled_pairwise / cnn_focal: F1 std `0.0328`, ECE mean `0.2205`

5. Error taxonomy indicates region-specific FN pressure that should be addressed in discussion.

| Region | Positive Support (approx) | FP | FN |
|---|---:|---:|---:|
| houston | 400 | 1 | 11 |
| nola | 500 | 43 | 10 |
| seattle | 590 | 5 | 15 |

## Significance Addendum

- source: `/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed.csv`
- datasets with `F1 rec>cmp (CI)=True`: `1/3`
- datasets with `ECE rec<cmp (CI)=True`: `3/3`

## Threshold-Robustness Addendum

- source: `/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed_summary.csv`
- non-zero regret profiles: `10/12`
- nola_pooled_pairwise/fp_heavy: mean_regret `86.000` (mean_rec_th `0.3500` vs mean_best_th `0.9500`)
- seattle_pooled_pairwise/fn_very_heavy: mean_regret `30.800` (mean_rec_th `0.6050` vs mean_best_th `0.3650`)
- houston_pooled_pairwise/fn_very_heavy: mean_regret `26.000` (mean_rec_th `0.9500` vs mean_best_th `0.0500`)

## True Unseen-Area Addendum

- source: `/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv`
- supported true-area splits: `8/8`
- low-support true-area splits: `0` (none)
- own_ship hgbt F1 range: `0.6667 - 0.7789`
- transfer negative-ΔF1 pairs: `1/6`
- transfer harbor coverage: `3` regions

## Manuscript Freeze Addendum

- source: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json`
- operator profile lock rows: `3`
- max locked mean regret: `2.000`

## Transfer-Model-Scan Addendum

- source: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan.json`
- source_region: `houston`
- recommended_model_under_scan_rule: `hgbt`
- selection_rule: `all_targets_ece_leq_max_then_max_min_target_f1_then_max_mean_target_f1_then_max_mean_delta_f1`
- recommended model summary: min target F1 `0.7897`, mean target F1 `0.8257`, max target ECE `0.0428`

## Multi-Source Transfer-Model-Scan Addendum

- source: `/Users/seoki/Desktop/research/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed.json`
- recommended combined-pass sources: `2/3`
- best combined-pass sources: `2/3`
- recommendation mismatch count (recommended vs best-combined model): `2`
- source summary csv: `/Users/seoki/Desktop/research/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed_source_summary.csv`

## Multi-Source Transfer Governance-Bridge Addendum

- source: `/Users/seoki/Desktop/research/docs/multisource_transfer_governance_bridge_2026-04-05_10seed.json`
- baseline combined-pass sources: `2/3`
- governed combined-pass sources: `3/3`
- improved source count after governance bridge: `1`
- governed detail csv: `/Users/seoki/Desktop/research/docs/multisource_transfer_governance_bridge_2026-04-05_10seed_detail.csv`

## Data-Algorithm Quality-Review Addendum

- source: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed.json`
- baseline combined-pass datasets: `2/3`
- final combined-pass datasets: `3/3`
- governance-improved datasets: `1`
- high-risk model rows: `19`
- todo rows: `0`
- DQ-5 acceptance met: `True`
- dataset scorecard csv: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed_dataset_scorecard.csv`
- high-risk models csv: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed_high_risk_models.csv`
- todo csv: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed_todo.csv`
- transfer override seed-stress json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed.json`
- manuscript freeze packet json: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json`
- transfer override seeds completed: `10/10`
- transfer-gate improved seed count: `10`
- DQ-3 acceptance met: `True`
- transfer override per-seed csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_per_seed.csv`
- model-claim stable recommendations: `3/3`
- model-claim appendix-only rows: `16`
- model-claim hygiene ready: `True`
- model-claim scope csv: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed_model_claim_scope.csv`
- model-claim caveat sentence: Reviewer caveat: Main-text model claims are restricted to recommended models that satisfy calibration (ECE<=0.10) and seed-variance (F1 std<=0.03) gates; models failing either gate are retained in appendix-only ablation tables.

## Transfer-Gap Diagnostics Addendum

- source: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics_summary.csv`
- negative ΔF1 pairs (fixed threshold): `2`
- negative ΔF1 pairs with CI upper<0: `0`
- pairs with target retune gain >=0.05 F1: `2`
- max target retune gain pair: `nola->houston:hgbt` (`0.1055`)

## Temporal-Robustness Addendum

- source: `/Users/seoki/Desktop/research/docs/temporal_robust_recommendation_2026-04-05_houston_10seed.json`
- recommendation changed datasets: `0/1`
- temporal target pass(current->robust): `0 -> 0`
- temporal target feasible datasets(any/ece-pass): `1 / 0`
- best observed out-of-time ΔF1 (any/ece-pass): `0.0727 / -0.1013`
- max robust in-time regression from best F1: `0.0000`

## Out-of-Time Threshold-Policy Addendum

- source: `/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.json`
- compared policies: `3`
- recommended policy (excluding oracle): `fixed_baseline_threshold`
- temporal gate threshold: `-0.0500`
- fixed_baseline_threshold: combined pass `2/3`, temporal pass `3/3`, mean ΔF1 `0.0711`, max OOT ECE `0.0377`
- oot_oracle_threshold: combined pass `2/3`, temporal pass `3/3`, mean ΔF1 `0.0877`, max OOT ECE `0.0377`
- oot_val_tuned: combined pass `1/3`, temporal pass `2/3`, mean ΔF1 `0.0402`, max OOT ECE `0.0377`
- houston(hgbt) ΔF1 val-tuned->fixed-baseline: `-0.1013->-0.0286` (combined pass: `no->yes`)

## Transfer-Policy Governance-Lock Addendum

- source: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed.json`
- selected transfer override: `rule_score/isotonic`
- baseline->projected negative pairs (global): `2->0`
- baseline->projected negative pairs (source): `2->0`
- out-of-time policy pass: `True`
- transfer policy pass: `True`
- governance ready for lock: `True`
- policy lock csv: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed_policy_lock.csv`
- projected transfer csv: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed_projected_transfer_check.csv`

## Transfer-Policy-Compare Addendum

- source: `/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_2026-04-05_10seed.json`
- compared shortlist models: `3`
- extra_trees: negative pairs fixed->retuned `2->2` (mean retune gain `0.0478`)
- hgbt: negative pairs fixed->retuned `2->2` (mean retune gain `0.0412`)
- random_forest: negative pairs fixed->retuned `2->2` (mean retune gain `0.0894`)

## Transfer-Policy-Compare (All Models) Addendum

- source: `/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_all_models_2026-04-05_10seed.json`
- compared models: `6`
- models with zero negative pairs after retune: `rule_score`
- extra_trees: pair_count `2`, negative fixed->retuned `2->2`, mean ΔF1 fixed->retuned `-0.1754->-0.1277`
- hgbt: pair_count `2`, negative fixed->retuned `2->2`, mean ΔF1 fixed->retuned `-0.1743->-0.1331`
- logreg: pair_count `2`, negative fixed->retuned `2->2`, mean ΔF1 fixed->retuned `-0.2309->-0.1945`
- random_forest: pair_count `2`, negative fixed->retuned `2->2`, mean ΔF1 fixed->retuned `-0.2049->-0.1155`
- rule_score: pair_count `2`, negative fixed->retuned `0->0`, mean ΔF1 fixed->retuned `0.5436->0.5942`
- torch_mlp: pair_count `2`, negative fixed->retuned `2->2`, mean ΔF1 fixed->retuned `-0.1763->-0.1498`

## Transfer-Calibration Probe Addendum

- source: `/Users/seoki/Desktop/research/docs/houston_transfer_calibration_probe_2026-04-05_10seed.json`
- combined-pass count (fixed/retuned): `1 / 1`
- methods scanned: `none, platt, isotonic`
- best fixed candidate: `rule_score/isotonic` (mean ΔF1 fixed `0.6032`, max target ECE `0.0684`)
- best retuned candidate: `rule_score/isotonic` (mean ΔF1 retuned `0.6058`, max target ECE `0.0684`)

## External-Validity Manuscript-Assets Addendum

- source: `/Users/seoki/Desktop/research/docs/external_validity_manuscript_assets_2026-04-05_10seed.json`
- transfer uncertainty directions covered: `6`
- scenario panels generated: `3`
- transfer table md: `/Users/seoki/Desktop/research/docs/external_validity_manuscript_assets_2026-04-05_10seed_transfer_uncertainty_table.md`
- scenario panel md: `/Users/seoki/Desktop/research/docs/external_validity_manuscript_assets_2026-04-05_10seed_scenario_panels.md`
- integration note md: `/Users/seoki/Desktop/research/docs/external_validity_manuscript_assets_2026-04-05_10seed.md`

## Priority TODO (Examiner View)

1. [Closed] Frozen unseen-area evidence statement prepared in manuscript freeze packet (`/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json`).
2. [Closed] Operator cost profile lock is frozen in manuscript freeze packet.
3. [Closed] Significance one-line caption addendum is frozen in manuscript freeze packet.

## Top-3 Models Per Dataset (10-seed aggregate)

### houston_pooled_pairwise

| Model | F1 mean±std (CI95) | ECE mean±std |
|---|---:|---:|
| hgbt | 0.8286±0.0000 (0.0000) | 0.0229±0.0000 |
| cnn_weighted | 0.8197±0.0274 (0.0170) | 0.1674±0.0268 |
| cnn_weighted_temp | 0.8195±0.0329 (0.0204) | 0.1620±0.0325 |

### nola_pooled_pairwise

| Model | F1 mean±std (CI95) | ECE mean±std |
|---|---:|---:|
| hgbt | 0.6015±0.0000 (0.0000) | 0.0237±0.0000 |
| random_forest | 0.5402±0.0218 (0.0135) | 0.0409±0.0016 |
| extra_trees | 0.5162±0.0156 (0.0096) | 0.0581±0.0012 |

### seattle_pooled_pairwise

| Model | F1 mean±std (CI95) | ECE mean±std |
|---|---:|---:|
| logreg | 0.8214±0.0000 (0.0000) | 0.0482±0.0000 |
| extra_trees | 0.8174±0.0261 (0.0162) | 0.0300±0.0017 |
| cnn_weighted | 0.8078±0.0088 (0.0055) | 0.3054±0.0293 |

