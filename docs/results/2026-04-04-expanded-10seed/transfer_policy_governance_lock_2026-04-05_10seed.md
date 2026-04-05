# Transfer Policy Governance Lock

## Inputs

- recommendation_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv`
- transfer_check_csv: `/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv`
- out_of_time_threshold_policy_compare_json: `/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.json`
- transfer_calibration_probe_detail_csv: `/Users/seoki/Desktop/research/docs/houston_transfer_calibration_probe_2026-04-05_10seed_detail.csv`
- source_region_for_transfer_override: `houston`
- metric_mode: `fixed`
- max_target_ece: `0.1000`
- max_negative_pairs_allowed: `1`
- required_out_of_time_policy: `fixed_baseline_threshold`

## Locked Decision

- selected transfer override candidate: `rule_score/isotonic`
- selected candidate pair count: `2`
- selected candidate negative pairs (mode=fixed): `0`
- selected candidate max target ECE: `0.0684`

## Transfer Gap Projection

- baseline negative pairs (global): `2/6`
- projected negative pairs (global): `0/6`
- baseline negative pairs (source=houston): `2`
- projected negative pairs (source=houston): `0`

## Governance Gate

- out-of-time policy pass (`fixed_baseline_threshold`): `True`
- transfer projection pass (negative pairs <= 1): `True`
- governance_ready_for_lock: `True`

## Outputs

- policy_lock_csv: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed_policy_lock.csv`
- projected_transfer_check_csv: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed_projected_transfer_check.csv`
- candidate_summary_csv: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed_candidate_summary.csv`
- summary_md: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed.md`
- summary_json: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed.json`
