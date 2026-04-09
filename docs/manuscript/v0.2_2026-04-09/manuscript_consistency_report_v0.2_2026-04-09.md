# Manuscript Consistency Report v0.2 (2026-04-09)

- Overall status: **PASS** (6/6)
- Generated from: `docs/results/2026-04-04-expanded-10seed`

| Check | Status | Detail |
| --- | --- | --- |
| Model-selection claim matches summary table | PASS | expected={'houston': 'hgbt', 'nola': 'hgbt', 'seattle': 'extra_trees'}, observed={'houston': 'hgbt', 'nola': 'hgbt', 'seattle': 'extra_trees'} |
| ECE gate claim holds for all selected models | PASS | all ece_mean_10seed <= 0.1 |
| Transfer-sign narrative matches computed deltas | PASS | Houston negative, NOLA positive, Seattle near-neutral/positive |
| Core figure assets exist | PASS | figure_1/2/3 svg files present |
| Threshold utility assets exist | PASS | figure_4 + threshold utility csv artifacts present |
| Core quantitative tables exist | PASS | recommended/transfer/significance/ablation/utility csv files present |

## Reviewer-Facing Notes
- Transfer CI is computed from source/target prediction CSV via bootstrap.
- Houston-source transfer is negative with narrow CI in this run, supporting domain-shift caution.
- Seattle transfer routes include zero in CI, so the claim is limited to near-neutral/weak-positive behavior.
