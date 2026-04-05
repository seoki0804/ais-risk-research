# Data & Algorithm Quality Review (10-Seed)

## Configuration

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- aggregate_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv`
- out_of_time_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_out_of_time_check_10seed/out_of_time_recommendation_check.csv`
- transfer_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv`
- out_of_time_threshold_policy_compare_json: `/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.json`
- multisource_transfer_governance_bridge_json: `/Users/seoki/Desktop/research/docs/multisource_transfer_governance_bridge_2026-04-05_10seed.json`
- transfer_override_seed_stress_test_json: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed.json`
- manuscript_freeze_packet_json: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json`

## Headline Status

- baseline combined-pass datasets: `2/3`
- final combined-pass datasets (after governance bridge): `3/3`
- governance-improved datasets: `1`
- high-risk model rows: `19`
- DQ-5 acceptance met (claim hygiene): `True`
- TODO items: `0`

## Transfer Override Seed-Stress Evidence

- completed seeds: `10/10`
- baseline fixed combined-pass: `0`
- override fixed combined-pass: `10`
- override better transfer-gate count: `10`
- DQ-3 acceptance met: `True`
- per-seed csv: `/Users/seoki/Desktop/research/docs/transfer_override_seed_stress_test_2026-04-05_10seed_per_seed.csv`

## Model-Claim Hygiene Freeze Evidence

- recommended stable claims: `3/3`
- appendix-only model rows: `16`
- recommended_claim_hygiene_ready: `True`
- DQ-5 acceptance met: `True`
- model_claim_scope_csv: `/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed_model_claim_scope.csv`
- caveat sentence: Reviewer caveat: Main-text model claims are restricted to recommended models that satisfy calibration (ECE<=0.10) and seed-variance (F1 std<=0.03) gates; models failing either gate are retained in appendix-only ablation tables.

## Dataset Scorecard

| Region | Recommended | F1±std | ECE | OOT ΔF1 | Transfer neg (base->gov) | Combined pass (base->final) | Risk |
|---|---|---:|---:|---:|---:|---|---|
| houston | hgbt | 0.8286±0.0000 | 0.0229 | -0.0286 | 2->0 | fail->pass | minimal |
| nola | hgbt | 0.6015±0.0000 | 0.0237 | 0.2254 | 0->0 | pass->pass | minimal |
| seattle | extra_trees | 0.8174±0.0261 | 0.0300 | 0.0164 | 0->0 | pass->pass | minimal |

## Detailed To-Do

1. [P3] No blocking quality issues detected in current configured gates.

## Output Files

- summary_md: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed.md`
- summary_json: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed.json`
- dataset_scorecard_csv: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed_dataset_scorecard.csv`
- high_risk_models_csv: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed_high_risk_models.csv`
- todo_csv: `/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed_todo.csv`
