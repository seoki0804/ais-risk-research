#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${ROOT}/outputs/2026-03-28_all_models_multiarea}"
SPLIT_STRATEGY="${SPLIT_STRATEGY:-own_ship}"
TORCH_DEVICE="${TORCH_DEVICE:-auto}"
INCLUDE_CNN="${INCLUDE_CNN:-1}"
CNN_LOSSES="${CNN_LOSSES:-weighted_bce,focal}"
AUTO_ADJUST_SPLIT="${AUTO_ADJUST_SPLIT:-1}"

mkdir -p "${OUTPUT_ROOT}"
regions=(houston nola seattle)

for region in "${regions[@]}"; do
  input_csv="${INPUT_DIR}/${region}_pooled_pairwise.csv"
  output_dir="${OUTPUT_ROOT}/${region}"
  cmd=(
    python -m ais_risk.all_models_cli
    --input "${input_csv}"
    --output-dir "${output_dir}"
    --split-strategy "${SPLIT_STRATEGY}"
    --torch-device "${TORCH_DEVICE}"
  )
  if [[ "${INCLUDE_CNN}" == "1" ]]; then
    cmd+=(--include-regional-cnn --cnn-losses "${CNN_LOSSES}")
  fi
  if [[ "${AUTO_ADJUST_SPLIT}" == "1" ]]; then
    cmd+=(--auto-adjust-split-for-support)
  fi

  echo "[run] ${region}"
  (
    cd "${ROOT}"
    PYTHONPATH=src "${cmd[@]}"
  )
done

(
  cd "${ROOT}"
  export OUTPUT_ROOT_ABS="${OUTPUT_ROOT}"
  PYTHONPATH=src python - <<'PY'
import csv
import os
from pathlib import Path

root = Path(os.environ["OUTPUT_ROOT_ABS"]).resolve()
csv_paths = sorted(root.glob("*/*_all_models_leaderboard.csv"))
rows = []
for path in csv_paths:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows.extend(list(csv.DictReader(handle)))

def to_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return -1.0

rows.sort(key=lambda row: (row.get("dataset", ""), 0 if row.get("status") == "completed" else 1, -to_float(row.get("f1", "")), row.get("model_name", "")))

out_csv = root / "all_models_multiarea_leaderboard.csv"
out_md = root / "all_models_multiarea_leaderboard.md"

if rows:
    fieldnames = list(rows[0].keys())
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

lines = [
    "# All Models Multi-Area Leaderboard",
    "",
    "| Dataset | Model | Family | Status | Positives | F1 | AUROC | ECE | Notes |",
    "|---|---|---|---|---:|---:|---:|---:|---|",
]
for row in rows:
    lines.append(
        "| {dataset} | {model} | {family} | {status} | {positives} | {f1:.4f} | {auroc:.4f} | {ece:.4f} | {notes} |".format(
                dataset=row.get("dataset", ""),
                model=row.get("model_name", ""),
                family=row.get("model_family", ""),
                status=row.get("status", ""),
                positives=row.get("positive_count", ""),
                f1=to_float(row.get("f1", "")),
                auroc=to_float(row.get("auroc", "")),
                ece=to_float(row.get("ece", "")),
                notes=str(row.get("notes", "")).replace("|", "/"),
            )
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"combined_csv={out_csv.resolve()}")
print(f"combined_md={out_md.resolve()}")
PY
)
