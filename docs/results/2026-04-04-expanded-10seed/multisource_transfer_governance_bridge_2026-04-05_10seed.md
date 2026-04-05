# Multi-Source Transfer Governance Bridge

- source summary csv: `/Users/seoki/Desktop/research/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed_source_summary.csv`
- policy lock json: `/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed.json`
- baseline_combined_pass_count: `2/3`
- governed_combined_pass_count: `3/3`
- improved_source_count: `1`

| Source | Baseline Model | Baseline Pass | Baseline Neg Pairs | Baseline Max ECE | Mode | Governed Model | Governed Method | Governed Pass | Governed Neg Pairs | Governed Max ECE |
|---|---|---:|---:|---:|---|---|---|---:|---:|---:|
| houston | hgbt | no | 2 | 0.0428 | transfer_override_locked | rule_score | isotonic | yes | 0 | 0.0684 |
| nola | hgbt | yes | 0 | 0.0260 | baseline_recommended | hgbt | - | yes | 0 | 0.0260 |
| seattle | random_forest | yes | 0 | 0.0220 | baseline_recommended | random_forest | - | yes | 0 | 0.0220 |
