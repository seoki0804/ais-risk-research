# Examiner-Critical TODO v0.2 (2026-04-09)

## Critical Findings (Objective Reviewer View)
1. **Novelty framing risk (high)**: the manuscript currently lacks an explicit related-work differential table.
2. **Statistical evidence risk (medium)**: family-level significance appendix is now attached, but transfer-route repeated-randomization testing is still pending.
3. **External validity risk (medium)**: transfer analysis is strong across three regions, but global regime diversity is still limited.
4. **Operational interpretation risk (low-medium)**: threshold utility appendix is attached, but deployment-profile calibration still needs stakeholder-specific tuning.
5. **Labeling protocol clarity risk (medium)**: near-miss/collision-proxy linkage is implied but not fully formalized against prior literature.

## Detailed TODO with Acceptance Criteria
- [ ] Add `Related Work Differential` subsection (5-8 key papers + one-line novelty delta for each).
  - Acceptance: manuscript includes a compact table that references `prior_work_evidence_matrix_v0.2_2026-04-09.md` IDs (`RW-01`~`RW-13`).
- [x] Add significance test appendix for tabular vs raster-CNN (`statistical_significance_appendix_v0.2_2026-04-09.md`).
  - Acceptance: report p-values with multiple-comparison control and effect-size-oriented interpretation notes.
- [x] Add bootstrap-based transfer-route significance summary (`transfer_route_significance_appendix_v0.2_2026-04-09.md`).
  - Acceptance: route-level table includes CI95, two-sided p-value, and direction probability.
- [ ] Extend significance testing to transfer deltas with repeated-randomization protocol.
  - Acceptance: route-level significance table includes repeated runs and corrected p-values.
- [x] Add one additional out-of-domain test split (new area/year) for robustness (`out_of_domain_validation_appendix_v0.2_2026-04-09.md`).
  - Acceptance: report includes same KPIs (`F1`, `ECE`, `ΔF1`, CI95) and explicitly states pass/fail gates.
- [x] Add threshold utility analysis (`threshold_utility_appendix_v0.2_2026-04-09.md`) for false-alarm vs miss-risk tradeoff.
  - Acceptance: operating-point table + curve-based figure are attached with explicit cost profile.
- [ ] Clarify label-generation policy with near-miss proxy grounding.
  - Acceptance: Methods section provides deterministic event rule and cites at least one AIS near-miss paper (`RW-03`).
- [x] Final bilingual publication pass (Korean + English).
  - Acceptance: KO/EN drafts have section/figure/table parity and terminology consistency check log (`bilingual_parity_report_v0.2_2026-04-09.md` = PASS).
