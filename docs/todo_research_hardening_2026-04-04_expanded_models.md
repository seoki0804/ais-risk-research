# To-Do: Research Hardening Plan (Expanded Models)

## Status Snapshot

- Completed:
  - all-model multi-area benchmark (tabular + CNN)
  - seed sweep aggregate/winner/recommendation
  - support-aware split auto-adjust
- Remaining:
  - calibration-gated final policy
  - out-of-time and unseen-area transfer hardening
  - reviewer-grade uncertainty and failure analysis packaging

## Action Items

1. `P1` Add calibration-gated recommendation policy.
   - Why: high-F1 CNN variants show high ECE in multiple regions.
   - Task:
     - implement ECE hard gate (`<=0.10`) before final recommendation selection.
     - keep rejected candidates in a separate audit table.
   - Done when:
     - recommendation file includes `accepted/rejected` reason.
     - at least one run artifact shows gate effect clearly.

2. `P1` Run out-of-time validation bundle.
   - Why: current evidence is strong for split-based holdout, weaker for strict time drift.
   - Task:
     - prepare one strict future-only block per region.
     - run all-model benchmark on each block with fixed thresholds from source validation.
   - Done when:
     - `F1/AUROC/ECE` degradation table exists for Houston/NOLA/Seattle.

3. `P1` Add true unseen-area transfer comparison.
   - Why: reviewers will ask if policy generalizes beyond same-ecosystem regions.
   - Task:
     - run `benchmark_transfer` for selected source/target pairs.
     - evaluate threshold portability and calibration drift.
   - Done when:
     - transfer summary includes per-model source vs target gap and recommendation.

4. `P2` Strengthen seed/stability evidence.
   - Why: neural and some CNN variants have higher seed variance.
   - Task:
     - increase seed count from `3` to `>=10` for final submission numbers.
     - export confidence intervals from aggregate table.
   - Done when:
     - summary includes mean/std and CI for all final candidates.

5. `P2` Publish reliability diagrams for final candidates.
   - Why: calibration quality is central to risk-map trust.
   - Task:
     - generate reliability plots for chosen model per region.
     - include pre/post temperature scaling curves when applicable.
   - Done when:
     - figure set contains region-wise reliability diagrams and ECE values.

6. `P2` Build error taxonomy appendix.
   - Why: qualitative failure interpretation is required for strong rebuttal readiness.
   - Task:
     - stratify FP/FN by encounter type, vessel type, distance/tcpa buckets.
     - extract representative failure cases with row-level traces.
   - Done when:
     - appendix table has recurring failure classes and mitigation notes.

7. `P3` Standardize publication packet generation.
   - Why: reproducibility and traceability for GitHub + manuscript sync.
   - Task:
     - add one script that creates final `docs/results/<date>` bundle from latest run root.
     - include manifest with input hashes and command logs.
   - Done when:
     - one command regenerates the full submission evidence bundle.

## Suggested Execution Order

1. Calibration gate (`P1`)
2. Out-of-time validation (`P1`)
3. Unseen-area transfer (`P1`)
4. Seed expansion and CI (`P2`)
5. Reliability diagrams (`P2`)
6. Error taxonomy appendix (`P2`)
7. Packet automation (`P3`)
