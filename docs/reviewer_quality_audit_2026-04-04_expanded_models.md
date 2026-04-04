# Reviewer Quality Audit (Expanded Models, 2026-04-04)

> Superseded by 10-seed audit: `docs/reviewer_quality_audit_2026-04-04_expanded_models_10seed.md`.

## Scope

- Run set:
  - `outputs/2026-04-04_all_models_multiarea_expanded`
  - `outputs/2026-04-04_all_models_seed_sweep_expanded`
- Data:
  - `Houston / NOLA / Seattle` pooled pairwise datasets
  - `own_ship` split with support-aware auto-adjust
- Model families:
  - tabular: `rule_score, logreg, hgbt, random_forest, extra_trees, torch_mlp`
  - raster CNN: `weighted_bce/focal` (+ temperature-scaled variants)

## Major Findings (Examiner View)

1. P1: Calibration risk blocks direct CNN deployment despite high single-run F1.
   - Seattle single-run top F1 is CNN (`0.8364`) but ECE is high (`0.2791`).
   - Houston single-run top F1 is also CNN-temp (`0.8315`) with ECE `0.1458`.
   - In seed-sweep recommendation, both Houston and Seattle prefer calibrated tabular models (`hgbt`, `logreg`) rather than CNN.

2. P1: Regional winner inconsistency indicates non-trivial domain sensitivity.
   - Houston/NOLA: `hgbt` dominates.
   - Seattle: `logreg` is selected under stability/calibration criteria.
   - Interpretation: one global model claim without region-aware policy is weak for peer review.

3. P2: Data support is usable but still limited for high-capacity models.
   - Test positives are around `40~59` by region after split auto-adjust.
   - This is enough for baseline comparison but still thin for robust CNN calibration/ablation claims.

4. P2: Neural model variance remains higher than tree/linear baselines.
   - `torch_mlp` F1 std is relatively high across regions (around `0.04` scale).
   - Some CNN variants also show noticeable seed sensitivity.

5. P2: Evidence hierarchy is good for baseline, not yet complete for publication-grade external validity.
   - Same-ecosystem multi-region and seed sweep are in place.
   - Missing stronger out-of-time and true unseen-area evidence in this expanded-model packet.

## Current Verdict

- Concept quality: strong (`AIS-only collision-risk learning + heatmap/contour operationalization`).
- Experimental quality: good for engineering validation, not yet fully publication-hardened.
- Deployment recommendation today:
  - primary: calibrated tabular per-region recommendation (`hgbt` for Houston/NOLA, `logreg` for Seattle)
  - secondary: CNN as analysis/comparison model, not default decision model.

## Priority To-Do (Publication Hardening)

1. P1: Add strict calibration gate to model selection.
   - Rule: reject candidates with `ECE > 0.10` for default deployment.
   - Output required: gated leaderboard + excluded-model log.

2. P1: Add out-of-time validation slice per region.
   - Minimum: one fully unseen time block per region.
   - Output required: delta table vs current split (`F1/AUROC/ECE` drop).

3. P1: Add true unseen-area transfer benchmark into the same recommendation logic.
   - Evaluate source->target transfer with unchanged threshold policy.
   - Output required: transfer recommendation table with confidence notes.

4. P2: Expand uncertainty reporting in final figures.
   - Add mean±std overlays from seed sweep on main performance figures.
   - Include calibration reliability curves for selected final models.

5. P2: Enforce sample-support governance in manuscript claims.
   - For each claim, report positive support (`n_pos`) and confidence caveat.
   - Block strong claims when support threshold is not met.

6. P2: Add reviewer-ready error taxonomy.
   - False-positive / false-negative cases by encounter context and vessel-type mix.
   - Include at least top-k recurring failure patterns per region.

## Acceptance Criteria for "Paper-Ready v1"

- Recommendation table is calibration-gated and reproducible from one command.
- Out-of-time + unseen-area transfer evidence is included beside same-area results.
- Main claim is tied to region-aware model policy, not single global winner.
- Every reported score in the paper has support count and seed-variance context.
