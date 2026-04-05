# GitHub Upload Checklist (2026-04-05)

## 1) Final Status Snapshot

- E2E rerun script: `examples/run_external_validity_checks_2026-04-04_10seed.sh` (completed)
- Data-algorithm quality review: `final_combined_pass=3/3`, `todo_count=0`
- DQ closure: `DQ-3=True`, `DQ-5=True`
- Manuscript freeze model-claim hygiene: `recommended_stable=3/3`, `appendix_only=16`, `ready=True`

Primary evidence:
- `docs/data_algorithm_quality_review_2026-04-05_10seed.json`
- `docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json`
- `docs/reviewer_quality_audit_2026-04-04_expanded_models_10seed.json`
- `docs/results/2026-04-04-expanded-10seed/bundle_manifest_2026-04-04-expanded-10seed.json`
- `docs/results/2026-04-04-expanded-10seed/external_validity_command_log_2026-04-04_10seed.txt`

## 2) Code Changes To Include

- `src/ais_risk/data_algorithm_quality_review.py`
- `src/ais_risk/data_algorithm_quality_review_cli.py`
- `src/ais_risk/reviewer_quality_audit.py`
- `examples/run_data_algorithm_quality_review_2026-04-05.sh`
- `examples/run_external_validity_checks_2026-04-04_10seed.sh`
- `examples/export_github_results_bundle_2026-04-04_expanded_10seed.sh`
- `tests/test_data_algorithm_quality_review_cli.py`
- `tests/test_data_algorithm_quality_review_dq5_closure.py`
- `tests/test_reviewer_quality_audit_data_algorithm_addendum.py`

## 3) Artifacts To Include

- `docs/data_algorithm_quality_review_2026-04-05_10seed.md`
- `docs/data_algorithm_quality_review_2026-04-05_10seed.json`
- `docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.md`
- `docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json`
- `docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed_model_claim_scope.csv`
- `docs/reviewer_quality_audit_2026-04-04_expanded_models_10seed.md`
- `docs/reviewer_quality_audit_2026-04-04_expanded_models_10seed.json`
- `docs/examiner_todo_2026-04-05_transfer_focus.md`
- `docs/results/2026-04-04-expanded-10seed/README.md`
- `docs/results/2026-04-04-expanded-10seed/bundle_manifest_2026-04-04-expanded-10seed.txt`
- `docs/results/2026-04-04-expanded-10seed/bundle_manifest_2026-04-04-expanded-10seed.json`
- `docs/results/2026-04-04-expanded-10seed/external_validity_command_log_2026-04-04_10seed.txt`

## 4) Validation Commands Executed

- `TMPDIR=/Users/seoki/Desktop/research/.tmp PYTHONPATH=src pytest -q tests/test_manuscript_freeze_packet.py tests/test_data_algorithm_quality_review.py tests/test_data_algorithm_quality_review_cli.py tests/test_data_algorithm_quality_review_dq3_closure.py tests/test_data_algorithm_quality_review_dq5_closure.py tests/test_reviewer_quality_audit.py tests/test_reviewer_quality_audit_cli.py tests/test_reviewer_quality_audit_data_algorithm_addendum.py tests/test_reviewer_quality_audit_multisource_addendum.py tests/test_reviewer_quality_audit_multisource_governance_bridge_addendum.py`
  - Result: `10 passed`
- `python -m py_compile src/ais_risk/data_algorithm_quality_review.py src/ais_risk/data_algorithm_quality_review_cli.py src/ais_risk/manuscript_freeze_packet.py src/ais_risk/manuscript_freeze_packet_cli.py src/ais_risk/reviewer_quality_audit.py`
- `bash -n examples/run_data_algorithm_quality_review_2026-04-05.sh examples/run_external_validity_checks_2026-04-04_10seed.sh examples/export_github_results_bundle_2026-04-04_expanded_10seed.sh`
- `TMPDIR=/Users/seoki/Desktop/research/.tmp bash examples/run_external_validity_checks_2026-04-04_10seed.sh`

## 5) PR Summary Draft

- Closed remaining quality gate actions by wiring manuscript-freeze claim-hygiene evidence into data-algorithm review (`DQ-5` auto-closure condition).
- Preserved existing DQ-3 seed-stress closure and surfaced both DQ-3/DQ-5 closure evidence in reviewer audit outputs.
- Hardened rerun stability by defaulting runner scripts to a workspace-local `TMPDIR`.
- Regenerated reviewer-facing artifacts and results bundle manifest/command-log after full E2E rerun.

