#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src"

run_area() {
  local area_slug="$1"
  local input_csv="$2"
  local output_dir="$3"

  mkdir -p "$output_dir"
  python -m ais_risk.regional_raster_cnn_cli \
    --input "$input_csv" \
    --output-prefix "$output_dir/${area_slug}_regional_raster_cnn_capped" \
    --split-strategy own_ship \
    --epochs 8 \
    --batch-size 32 \
    --learning-rate 0.001 \
    --max-train-rows 1024 \
    --max-val-rows 256 \
    --max-test-rows 256 \
    --torch-device auto
}

run_area \
  "houston" \
  "/Users/seoki/Desktop/research/outputs/2026-03-14_noaa_houston_exploratory_pairwise/houston_pairwise.csv" \
  "/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_houston_capped"

run_area \
  "seattle" \
  "/Users/seoki/Desktop/research/outputs/2026-03-14_noaa_seattle_exploratory_pairwise/seattle_pairwise.csv" \
  "/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_seattle_capped"

python - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

items = [
    ("Houston", Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_houston_capped/houston_regional_raster_cnn_capped_summary.json")),
    ("Seattle", Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_seattle_capped/seattle_regional_raster_cnn_capped_summary.json")),
]
rows = []
for area, path in items:
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    rows.append(
        {
            "area": area,
            "f1": float(metrics["f1"]),
            "auroc": float(metrics["auroc"]) if metrics.get("auroc") is not None else None,
            "auprc": float(metrics["auprc"]) if metrics.get("auprc") is not None else None,
            "precision": float(metrics["precision"]),
            "recall": float(metrics["recall"]),
            "positive_rate_predicted": float(metrics["positive_rate_predicted"]),
            "threshold": float(metrics["threshold"]),
        }
    )

csv_path = Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_capped_summary_61day.csv")
md_path = Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_capped_summary_61day.md")
with csv_path.open("w", encoding="utf-8") as handle:
    handle.write("area,f1,auroc,auprc,precision,recall,positive_rate_predicted,threshold\n")
    for row in rows:
        handle.write(
            "{area},{f1:.6f},{auroc:.6f},{auprc:.6f},{precision:.6f},{recall:.6f},{positive_rate_predicted:.6f},{threshold:.2f}\n".format(
                **row
            )
        )

lines = [
    "# Regional Raster CNN Capped Summary 61day",
    "",
    "| Area | F1 | AUROC | AUPRC | Precision | Recall | Predicted Positive Rate | Threshold |",
    "|---|---:|---:|---:|---:|---:|---:|---:|",
]
for row in rows:
    lines.append(
        "| {area} | {f1:.4f} | {auroc:.4f} | {auprc:.4f} | {precision:.4f} | {recall:.4f} | {positive_rate_predicted:.4f} | {threshold:.2f} |".format(
            **row
        )
    )
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(csv_path)
print(md_path)
PY
