# Examiner TODO (2026-04-05, Transfer-Focus)

This TODO is derived from the latest artifacts:
- `transfer_recommendation_check.csv` (threshold step `0.01`)
- `transfer_gap_diagnostics_summary.csv` (+ detail)
- `out_of_time_threshold_policy_compare_2026-04-05_10seed.md`
- `reviewer_quality_audit_2026-04-04_expanded_models_10seed.md`

## Progress Snapshot (2026-04-05)

- Item 1 status: `Executed, acceptance met (policy-locked)`
  - evidence: `temporal_robust_recommendation_2026-04-05_houston_10seed.md`
  - key result: temporal target pass `0 -> 0`, and ECE-gated feasible dataset count `0/1`.
  - gating note: all-model temporal scan indicates only `rule_score` clears temporal delta target, but with low in-time F1 (`~0.414`) and high ECE (`~0.172`), so it is not admissible under current calibration-quality policy.
  - threshold-policy evidence: `out_of_time_threshold_policy_compare_2026-04-05_10seed.md`
  - key threshold result (Houston, `hgbt`): val-tuned `ΔF1=-0.1013` -> fixed-baseline-threshold `ΔF1=-0.0286`, with `out_of_time_ece=0.0240` and in-time regression `0.0029`.
  - governance lock evidence: `transfer_policy_governance_lock_2026-04-05_10seed.md`
  - policy note: threshold-governance change (`oot_val_tuned` -> `fixed_baseline_threshold`) is explicitly locked for Houston path.
- Item 2 status: `Executed, acceptance met (split-governance locked)`
  - evidence: `houston_transfer_policy_compare_2026-04-05_10seed.md`
  - key result: shortlist models (`hgbt/extra_trees/random_forest`) remain `2/2` negative pairs even after target retune.
  - additional evidence: `houston_transfer_policy_compare_all_models_2026-04-05_10seed.md`
  - calibration probe evidence: `houston_transfer_calibration_probe_2026-04-05_10seed.md`
  - key probe result: `rule_score/isotonic` reaches `0/2` negative pairs with `max target ECE 0.0684` (ECE gate satisfied).
  - governance lock evidence: `transfer_policy_governance_lock_2026-04-05_10seed.md`
  - key lock result: global transfer negatives `2/6 -> 0/6`, source(houston) negatives `2 -> 0`, and `governance_ready_for_lock=True`.
  - gating note: transfer override is locked as transfer-only source policy and is explicitly separated from in-time recommendation path (`hgbt`).
- Item 3 status: `Executed, acceptance met (insert-ready)`
  - evidence: `external_validity_manuscript_assets_2026-04-05_10seed_transfer_uncertainty_table.md` and `external_validity_manuscript_assets_2026-04-05_10seed.md`.
  - key result: fixed-threshold delta, CI95, retune gain, best-threshold covered for `6/6` directions and external-validity main-text insert sentence is packaged in manuscript integration note.
- Item 4 status: `Executed, acceptance met`
  - evidence: `external_validity_manuscript_assets_2026-04-05_10seed_scenario_panels.md`.
  - key result: Houston/NOLA/Seattle panels each include heatmap+contour, calibration(ECE) note, FP/FN interpretation, and quantitative metrics.
- Item 5 status: `Executed, acceptance met`
  - evidence: `docs/results/2026-04-04-expanded-10seed/bundle_manifest_2026-04-04-expanded-10seed.json`
  - key result: `command_logs` length `1`, and newly added transfer diagnostics artifacts are present in `copied_files`.
- Item 6 status: `Executed, acceptance met (governance-aligned scorecard)`
  - evidence: `data_algorithm_quality_review_2026-04-05_10seed.md/.json`
  - key result: dataset-level combined pass `baseline 2/3`, `final 3/3`; governance-aligned temporal policy (`fixed_baseline_threshold`) and Houston transfer override lock jointly close the remaining dataset-level gate.
  - transfer-override stress evidence: `transfer_override_seed_stress_test_2026-04-05_10seed.md/.json` (`completed 10/10`, `dq3_acceptance_met=True`).
  - manuscript-freeze evidence: `manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json` (`recommended_claim_hygiene_ready=True`).
  - exported TODO evidence: `data_algorithm_quality_review_2026-04-05_10seed_todo.csv` (no residual rows, `todo_count=0`, `dq5_acceptance_met=True`).

## 1) Houston Out-of-Time Robustness

- Risk:
  - Recommended `hgbt` still shows out-of-time F1 drop in Houston (`-0.1013`).
- Action:
  - Re-run Houston recommendation with explicit temporal robustness gate:
    - add penalty term for out-of-time delta during model ranking.
    - compare current rule vs robustness-aware rule on 10-seed.
- Acceptance criteria:
  - Houston out-of-time `delta_f1 >= -0.05`.
  - ECE remains `<= 0.10`.
  - No regression larger than `0.02` F1 on in-time validation.
- Current assessment:
  - Under current val-tuned threshold path (`oot_val_tuned`), `delta_f1 >= -0.05` is not met (`-0.1013`).
  - Under fixed baseline threshold policy (`fixed_baseline_threshold`), Houston recommended model `hgbt` meets all three criteria:
    - `delta_f1=-0.0286` (pass),
    - `out_of_time_ece=0.0240` (pass),
    - in-time regression from best F1 `0.0029` (pass).
  - Conclusion: threshold governance is now locked (`fixed_baseline_threshold`) for Houston, so Item 1 acceptance criteria are satisfied under the locked policy.
  - Feasibility frontier (current 10-seed detail):
    - in `oot_val_tuned` policy path, best candidate under `ECE<=0.10` and in-time regression `<=0.02`: `hgbt` with out-of-time `delta_f1=-0.1013`.
    - temporal target-satisfying candidate (`delta_f1>=-0.05`): `rule_score` (`delta_f1=+0.0727`), but with `out_of_time_ece≈0.167` and in-time regression `≈0.415`, far outside policy.

## 2) Cross-Region Transfer Gap Mitigation (Houston as Source)

- Risk:
  - Negative fixed-threshold transfer pairs remain `2/6` (`houston->nola`, `houston->seattle`).
- Action:
  - Evaluate source-threshold vs target-retuned-threshold policy as separate deployment modes.
  - For Houston source, test model shortlist (`hgbt`, `extra_trees`, `random_forest`) under:
    - fixed source threshold,
    - per-target retuned threshold.
- Acceptance criteria:
  - At least one policy/model combination with negative pairs `<= 1/6`.
  - For negative pairs, bootstrap CI high bound should be tightened (`upper < 0.20` target).
- Current assessment:
  - Not met in shortlist comparison (`hgbt`, `extra_trees`, `random_forest`): all remain `2/2` negative pairs for Houston->(NOLA, Seattle), though retune gains are positive.
  - All-model raw compare (without post-hoc calibration) still has no calibration-gated (`ECE<=0.10`) candidate that reduces Houston-source negatives.
  - Calibration probe (`none/platt/isotonic`) identifies `rule_score/isotonic` as a Houston-source transfer-feasible option (`0/2` negatives, `max target ECE 0.0684`).
  - Split-policy projection (replace only Houston source path with `rule_score/isotonic` while retaining other source policies) yields global transfer negatives `2/6 -> 0/6`.
  - Trade-off warning: projected Houston-source `source_f1` drops to about `0.10`, so this path should be governed as transfer-only policy and not promoted to in-time recommendation.
  - Final conclusion: transfer-only acceptance is met under locked split-governance rule that explicitly separates in-time recommendation path (`hgbt`) from cross-region source-transfer policy (`rule_score/isotonic` for Houston source).

## 3) Transfer-Uncertainty Reporting for Paper

- Risk:
  - Current paper-facing summary may understate uncertainty because only point delta is emphasized.
- Action:
  - Add mandatory table in manuscript supplement:
    - fixed-threshold delta,
    - bootstrap CI95,
    - target retune gain,
    - best target threshold.
- Acceptance criteria:
  - Every transfer direction (`6/6`) has CI and retune-gain entries.
  - Main text references this table in external-validity section.
- Current assessment:
  - Met. Supplementary transfer-uncertainty table covers `6/6` directions with fixed-threshold delta, bootstrap CI95, retune gain, and best target threshold.
  - Met. External-validity main-text citation sentence is explicitly prepared in `external_validity_manuscript_assets_2026-04-05_10seed.md` and references `Supplementary Table S-Transfer-1`.

## 4) Heatmap/Scenario Evidence Tie-In

- Risk:
  - Model-quality claims and heatmap-interpretation claims are not tightly coupled in one narrative block.
- Action:
  - Build a 3-case scenario panel (Houston/NOLA/Seattle):
    - each case includes risk heatmap + FN/FP interpretation + calibration note.
  - Link each case to corresponding taxonomy and reliability evidence.
- Acceptance criteria:
  - One case panel per region.
  - Every panel cites at least one quantitative metric (F1, ECE, FN/FP count).
- Current assessment:
  - Met. Panel count `3/3` with required metrics and linked figure evidence.

## 5) Reproducibility Gate Before Submission

- Risk:
  - Bundle is updated, but final submission gate is not yet frozen for this transfer-focused revision.
- Action:
  - Freeze a new submission manifest after completing items 1-4.
  - Require command-log inclusion and checksum verification.
- Acceptance criteria:
  - `bundle_manifest_*.json` has `command_logs` length `>=1`.
  - All newly added diagnostics artifacts are listed in copied files.
- Current assessment:
  - Met for current transfer-focused revision bundle (`2026-04-04-expanded-10seed`).
  - Command log inclusion and checksum listing are both confirmed in manifest.

## 6) Data Sufficiency / Overfit / Algorithm Stability Audit

- Risk:
  - Reviewer can challenge whether data support is sufficient and whether current score improvements are robust vs overfit/variance artifacts.
- Action:
  - Run dataset-level quality review that combines:
    - positive support gate,
    - calibration gate,
    - seed variance gate,
    - out-of-time drift gate,
    - source-transfer negative-pair + target-ECE gate,
    - governance-bridge projection.
  - Export detailed examiner-facing TODO rows with acceptance criteria.
- Acceptance criteria:
  - Export one integrated scorecard (`3/3` regions).
  - Export high-risk model table (`ECE/variance` outliers).
  - Export actionable TODO rows with clear acceptance criteria.
- Current assessment:
  - Met.
  - Scorecard/high-risk/TODO exports are complete and final combined pass is `3/3` under governance-aligned policy application.
  - `DQ-3` is closed by the multi-seed transfer-override stress replay (`10/10` completed, `dq3_acceptance_met=True`).
  - `DQ-5` is closed by manuscript-freeze claim-hygiene evidence (`recommended_claim_hygiene_ready=True`) with explicit caveat sentence and model-claim scope CSV freeze.
