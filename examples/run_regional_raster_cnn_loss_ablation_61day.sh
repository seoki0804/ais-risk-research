#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src"

run_variant() {
  local area_slug="$1"
  local input_csv="$2"
  local loss_type="$3"
  local output_dir="$4"

  mkdir -p "$output_dir"
  python -m ais_risk.regional_raster_cnn_cli \
    --input "$input_csv" \
    --output-prefix "$output_dir/${area_slug}_regional_raster_cnn_${loss_type}" \
    --split-strategy own_ship \
    --epochs 8 \
    --batch-size 32 \
    --learning-rate 0.001 \
    --loss-type "$loss_type" \
    --focal-gamma 2.0 \
    --max-train-rows 1024 \
    --max-val-rows 256 \
    --max-test-rows 256 \
    --torch-device auto
}

run_variant \
  "houston" \
  "/Users/seoki/Desktop/research/outputs/2026-03-14_noaa_houston_exploratory_pairwise/houston_pairwise.csv" \
  "weighted_bce" \
  "/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_houston"

run_variant \
  "houston" \
  "/Users/seoki/Desktop/research/outputs/2026-03-14_noaa_houston_exploratory_pairwise/houston_pairwise.csv" \
  "focal" \
  "/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_houston"

run_variant \
  "seattle" \
  "/Users/seoki/Desktop/research/outputs/2026-03-14_noaa_seattle_exploratory_pairwise/seattle_pairwise.csv" \
  "weighted_bce" \
  "/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_seattle"

run_variant \
  "seattle" \
  "/Users/seoki/Desktop/research/outputs/2026-03-14_noaa_seattle_exploratory_pairwise/seattle_pairwise.csv" \
  "focal" \
  "/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_seattle"

python - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

items = [
    ("Houston", "weighted_bce", Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_houston/houston_regional_raster_cnn_weighted_bce_summary.json")),
    ("Houston", "focal", Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_houston/houston_regional_raster_cnn_focal_summary.json")),
    ("Seattle", "weighted_bce", Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_seattle/seattle_regional_raster_cnn_weighted_bce_summary.json")),
    ("Seattle", "focal", Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_seattle/seattle_regional_raster_cnn_focal_summary.json")),
]
rows = []
for area, loss_type, path in items:
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    cal = payload["calibration_metrics"]
    rows.append(
        {
            "area": area,
            "loss_type": loss_type,
            "f1": float(metrics["f1"]),
            "auroc": float(metrics["auroc"]) if metrics.get("auroc") is not None else None,
            "auprc": float(metrics["auprc"]) if metrics.get("auprc") is not None else None,
            "precision": float(metrics["precision"]),
            "recall": float(metrics["recall"]),
            "predicted_positive_rate": float(metrics["positive_rate_predicted"]),
            "threshold": float(metrics["threshold"]),
            "brier": float(cal["brier_score"]),
            "ece": float(cal["ece"]),
            "temp_f1": float(payload["temperature_scaling"]["metrics"]["f1"]) if payload["temperature_scaling"]["metrics"].get("status") != "skipped" else None,
            "temp_threshold": float(payload["temperature_scaling"]["metrics"]["threshold"]) if payload["temperature_scaling"]["metrics"].get("status") != "skipped" else None,
            "temperature": float(payload["temperature_scaling"]["temperature"]),
            "temp_brier": float(payload["temperature_scaled_calibration_metrics"]["brier_score"]),
            "temp_ece": float(payload["temperature_scaled_calibration_metrics"]["ece"]),
        }
    )

csv_path = Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_summary_61day.csv")
md_path = Path("/Users/seoki/Desktop/research/outputs/2026-03-16_regional_raster_cnn_loss_ablation_summary_61day.md")
with csv_path.open("w", encoding="utf-8") as handle:
    handle.write("area,loss_type,f1,auroc,auprc,precision,recall,predicted_positive_rate,threshold,brier,ece,temp_f1,temp_threshold,temperature,temp_brier,temp_ece\n")
    for row in rows:
        handle.write(
            "{area},{loss_type},{f1:.6f},{auroc:.6f},{auprc:.6f},{precision:.6f},{recall:.6f},{predicted_positive_rate:.6f},{threshold:.2f},{brier:.6f},{ece:.6f},{temp_f1:.6f},{temp_threshold:.2f},{temperature:.6f},{temp_brier:.6f},{temp_ece:.6f}\n".format(
                **row
            )
        )

lines = [
    "# Regional Raster CNN Loss Ablation Summary 61day",
    "",
    "| Area | Loss | Raw F1 | AUROC | AUPRC | Pred+ | Raw Thr | Raw Brier | Raw ECE | Temp | Temp F1 | Temp Thr | Temp Brier | Temp ECE |",
    "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
]
for row in rows:
    lines.append(
        "| {area} | {loss_type} | {f1:.4f} | {auroc:.4f} | {auprc:.4f} | {predicted_positive_rate:.4f} | {threshold:.2f} | {brier:.4f} | {ece:.4f} | {temperature:.3f} | {temp_f1:.4f} | {temp_threshold:.2f} | {temp_brier:.4f} | {temp_ece:.4f} |".format(
            **row
        )
    )
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(csv_path)
print(md_path)
PY
