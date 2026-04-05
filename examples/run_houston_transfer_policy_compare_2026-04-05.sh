#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRANSFER_MODEL_SCAN_DETAIL_CSV="${TRANSFER_MODEL_SCAN_DETAIL_CSV:-${ROOT}/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan_detail.csv}"
WORKDIR="${WORKDIR:-${ROOT}/outputs/2026-04-05_transfer_policy_compare_10seed}"
SHORTLIST_MODELS="${SHORTLIST_MODELS:-hgbt,extra_trees,random_forest}"
TRANSFER_CHECK_LIKE_CSV="${TRANSFER_CHECK_LIKE_CSV:-${WORKDIR}/houston_shortlist_transfer_check_like.csv}"
GAP_OUTPUT_PREFIX="${GAP_OUTPUT_PREFIX:-${WORKDIR}/houston_shortlist_transfer_gap}"
SUMMARY_PREFIX="${SUMMARY_PREFIX:-${ROOT}/docs/houston_transfer_policy_compare_2026-04-05_10seed}"

mkdir -p "${WORKDIR}"

(
  cd "${ROOT}"
  env TRANSFER_MODEL_SCAN_DETAIL_CSV="${TRANSFER_MODEL_SCAN_DETAIL_CSV}" \
      SHORTLIST_MODELS="${SHORTLIST_MODELS}" \
      TRANSFER_CHECK_LIKE_CSV="${TRANSFER_CHECK_LIKE_CSV}" \
      python - <<'PY'
import csv
import os
from pathlib import Path

src = Path(os.environ["TRANSFER_MODEL_SCAN_DETAIL_CSV"]).resolve()
dst = Path(os.environ["TRANSFER_CHECK_LIKE_CSV"]).resolve()
keep = {token.strip() for token in os.environ["SHORTLIST_MODELS"].split(",") if token.strip()}
rows = []
for row in csv.DictReader(src.open("r", encoding="utf-8", newline="")):
    if row.get("model_name") not in keep:
        continue
    if row.get("status") != "completed":
        continue
    rows.append(
        {
            "source_region": row.get("source_region", ""),
            "target_region": row.get("target_region", ""),
            "recommended_model": row.get("model_name", ""),
            "status": row.get("status", ""),
            "threshold": row.get("threshold", ""),
            "transfer_summary_json_path": row.get("transfer_summary_json_path", ""),
        }
    )

dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "source_region",
            "target_region",
            "recommended_model",
            "status",
            "threshold",
            "transfer_summary_json_path",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
print(f"transfer_check_like_csv={dst}")
print(f"pair_rows={len(rows)}")
PY

  env PYTHONPATH=src python -m ais_risk.transfer_gap_diagnostics_cli \
    --transfer-check-csv "${TRANSFER_CHECK_LIKE_CSV}" \
    --output-prefix "${GAP_OUTPUT_PREFIX}" \
    --threshold-grid-step 0.01 \
    --bootstrap-samples 500 \
    --random-seed 42

  env GAP_DETAIL_CSV="${GAP_OUTPUT_PREFIX}_detail.csv" \
      SUMMARY_PREFIX="${SUMMARY_PREFIX}" \
      python - <<'PY'
import csv
import json
import os
from pathlib import Path
from statistics import mean

detail = Path(os.environ["GAP_DETAIL_CSV"]).resolve()
summary_prefix = Path(os.environ["SUMMARY_PREFIX"]).resolve()
rows = [row for row in csv.DictReader(detail.open("r", encoding="utf-8", newline="")) if row.get("status") == "completed"]
by_model = {}
for row in rows:
    model = str(row.get("model_name", "")).strip()
    if not model:
        continue
    by_model.setdefault(model, []).append(row)

summary_rows = []
for model in sorted(by_model.keys()):
    model_rows = by_model[model]
    fixed = [float(row["delta_f1_fixed_threshold"]) for row in model_rows if row.get("delta_f1_fixed_threshold")]
    retuned = [float(row["delta_f1_if_target_retuned"]) for row in model_rows if row.get("delta_f1_if_target_retuned")]
    gains = [float(row["target_retune_gain_f1"]) for row in model_rows if row.get("target_retune_gain_f1")]
    summary_rows.append(
        {
            "model_name": model,
            "pair_count": len(model_rows),
            "negative_fixed_count": sum(1 for value in fixed if value < 0.0),
            "negative_retuned_count": sum(1 for value in retuned if value < 0.0),
            "negative_fixed_ci_count": sum(
                1 for row in model_rows if str(row.get("delta_f1_ci_excludes_zero_negative", "")).lower() == "true"
            ),
            "mean_delta_f1_fixed": mean(fixed) if fixed else None,
            "mean_delta_f1_retuned": mean(retuned) if retuned else None,
            "mean_retune_gain_f1": mean(gains) if gains else None,
            "max_retune_gain_f1": max(gains) if gains else None,
        }
    )

summary_csv = summary_prefix.with_suffix(".csv")
summary_md = summary_prefix.with_suffix(".md")
summary_json = summary_prefix.with_suffix(".json")
fieldnames = [
    "model_name",
    "pair_count",
    "negative_fixed_count",
    "negative_retuned_count",
    "negative_fixed_ci_count",
    "mean_delta_f1_fixed",
    "mean_delta_f1_retuned",
    "mean_retune_gain_f1",
    "max_retune_gain_f1",
]
with summary_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(summary_rows)

def fmt(value: object, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "n/a"

lines = [
    "# Houston Transfer Policy Compare (Shortlist)",
    "",
    "## Inputs",
    "",
    f"- gap_detail_csv: `{detail}`",
    "- source_region: `houston`",
    "- shortlist: `hgbt, extra_trees, random_forest`",
    "- policy comparison: `fixed source threshold` vs `target-retuned threshold`",
    "",
    "## Model Summary",
    "",
    "| Model | Pairs | Negative(Fixed) | Negative(Retuned) | Mean ΔF1 Fixed | Mean ΔF1 Retuned | Mean Retune Gain | Max Retune Gain |",
    "|---|---:|---:|---:|---:|---:|---:|---:|",
]
for row in summary_rows:
    lines.append(
        "| {model} | {pairs} | {neg_fixed} | {neg_retuned} | {d_fixed} | {d_retuned} | {gain_mean} | {gain_max} |".format(
            model=row.get("model_name", ""),
            pairs=row.get("pair_count", 0),
            neg_fixed=row.get("negative_fixed_count", 0),
            neg_retuned=row.get("negative_retuned_count", 0),
            d_fixed=fmt(row.get("mean_delta_f1_fixed")),
            d_retuned=fmt(row.get("mean_delta_f1_retuned")),
            gain_mean=fmt(row.get("mean_retune_gain_f1")),
            gain_max=fmt(row.get("max_retune_gain_f1")),
        )
    )
lines.extend(
    [
        "",
        "## Outputs",
        "",
        f"- summary_csv: `{summary_csv}`",
        f"- summary_json: `{summary_json}`",
        f"- summary_md: `{summary_md}`",
        "",
    ]
)
summary_md.write_text("\n".join(lines), encoding="utf-8")
summary_json.write_text(
    json.dumps(
        {
            "status": "completed",
            "summary_csv_path": str(summary_csv),
            "summary_json_path": str(summary_json),
            "summary_md_path": str(summary_md),
            "rows": summary_rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"summary_md={summary_md}")
print(f"summary_json={summary_json}")
print(f"summary_csv={summary_csv}")
PY
)

echo "transfer_check_like_csv=${TRANSFER_CHECK_LIKE_CSV}"
echo "transfer_gap_md=${GAP_OUTPUT_PREFIX}.md"
echo "policy_compare_md=${SUMMARY_PREFIX}.md"
