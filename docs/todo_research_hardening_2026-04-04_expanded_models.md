# To-Do: Research Hardening Plan (Expanded Models)

## Status Snapshot

- Completed:
  - all-model multi-area benchmark (tabular + CNN)
  - seed sweep aggregate/winner/recommendation
  - calibration-gated recommendation policy (`ECE<=0.10`)
  - out-of-time(timestamp split) recommendation check
  - cross-region transfer recommendation check
  - support-aware split auto-adjust
- Remaining:
  - post-core reviewer closure:
    - raise positive support on low-support true-area splits (`Savannah`, `LA/LB own_ship`)
    - maintain/update multi-harbor unseen transfer evidence package

## Action Items

1. `P1` Add calibration-gated recommendation policy.
   - Why: high-F1 CNN variants show high ECE in multiple regions.
   - Task:
     - implement ECE hard gate (`<=0.10`) before final recommendation selection.
     - keep rejected candidates in a separate audit table.
   - Status: `DONE`
   - Evidence:
     - `all_models_seed_sweep_recommendation.csv` includes gate columns (`gate_status`, `ece_gate_*`).
     - `all_models_seed_sweep_summary.md` includes gate settings.

2. `P1` Run out-of-time validation bundle.
   - Why: current evidence is strong for split-based holdout, weaker for strict time drift.
   - Task:
     - prepare one strict future-only block per region.
     - run all-model benchmark on each block with fixed thresholds from source validation.
   - Status: `DONE`
   - Evidence:
     - `out_of_time_recommendation_check.csv/.md` exists for Houston/NOLA/Seattle.

3. `P1` Add true unseen-area transfer comparison.
   - Why: reviewers will ask if policy generalizes beyond same-ecosystem regions.
   - Task:
     - run `benchmark_transfer` for selected source/target pairs.
     - evaluate threshold portability and calibration drift.
   - Status: `DONE`
   - Evidence:
     - `transfer_recommendation_check.csv/.md` includes source→target `ΔF1/ΔAUROC/target ECE`.

4. `P2` Strengthen seed/stability evidence.
   - Why: neural and some CNN variants have higher seed variance.
   - Task:
     - increase seed count from `3` to `>=10` for final submission numbers.
     - export confidence intervals from aggregate table.
   - Status: `DONE`
   - Progress:
     - aggregate now includes `CI95` columns (`f1_ci95`, `auroc_ci95`, `ece_ci95`, `brier_ci95`).
     - 10-seed runner added: `examples/run_all_models_seed_sweep_10seed_2026-04-04.sh`.
     - 10-seed run completed: `outputs/2026-04-04_all_models_seed_sweep_10seed`.
     - external-validity 10-seed package completed: `docs/results/2026-04-04-expanded-10seed`.

5. `P2` Publish reliability diagrams for final candidates.
   - Why: calibration quality is central to risk-map trust.
   - Task:
   - generate reliability plots for chosen model per region.
   - include pre/post temperature scaling curves when applicable.
   - Status: `DONE`
   - Evidence:
     - `reliability_recommended_region_summary.csv`
     - `reliability_recommended_bins.csv`
     - `houston_recommended_reliability.png`
     - `nola_recommended_reliability.png`
     - `seattle_recommended_reliability.png`
     - `reliability_recommended_summary.md/.json`

6. `P2` Build error taxonomy appendix.
   - Why: qualitative failure interpretation is required for strong rebuttal readiness.
   - Task:
   - stratify FP/FN by encounter type, vessel type, distance/tcpa buckets.
   - extract representative failure cases with row-level traces.
   - Status: `DONE`
   - Evidence:
     - `error_taxonomy_region_summary.csv`
     - `error_taxonomy_details.csv`
     - `error_taxonomy_summary.md/.json`

7. `P3` Standardize publication packet generation.
   - Why: reproducibility and traceability for GitHub + manuscript sync.
   - Task:
     - add one script that creates final `docs/results/<date>` bundle from latest run root.
     - include manifest with input hashes and command logs.
   - Status: `DONE`
   - Progress:
     - bundle export script includes seed-sweep + OOT + transfer + reliability + taxonomy artifacts.
     - one-shot external validity runner exists.
   - manifest now includes copied-file SHA256, input-data SHA256, command-log SHA256, and git commit/dirty state.

8. `P1` Expand independent-harbor unseen-area evidence.
   - Why: examiner risk is concentrated in "outside current ecosystem" generalization questions.
   - Task:
   - add additional unseen-area/cross-year transfer evidence paths and integrate into one examiner-facing report.
   - keep support-threshold diagnostics (`test positives`) explicit in summary table and audit TODO wording.
   - Status: `DONE`
   - Evidence:
     - `docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed.md/.json`
     - includes NY/NJ 2024 pooled split evidence and LA/LB 2023↔2024 transfer results.

## Suggested Execution Order

1. Calibration gate (`P1`)
2. Out-of-time validation (`P1`)
3. Unseen-area transfer (`P1`)
4. Seed expansion and CI (`P2`)
5. Reliability diagrams (`P2`)
6. Error taxonomy appendix (`P2`)
7. Packet automation (`P3`)
