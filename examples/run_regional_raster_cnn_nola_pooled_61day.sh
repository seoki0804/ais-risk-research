#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src"

BASE_DIR="${BASE_DIR:-/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
INPUT_CSV="${INPUT_CSV:-$BASE_DIR/nola_pooled_pairwise.csv}"
OUTPUT_DIR="${OUTPUT_DIR:-/Users/seoki/Desktop/research/outputs/2026-03-19_regional_raster_cnn_nola_pooled_leakfix}"

mkdir -p "$OUTPUT_DIR"

run_variant() {
  local loss_type="$1"
  local output_prefix="$OUTPUT_DIR/nola_regional_raster_cnn_pooled_${loss_type}"

  python -m ais_risk.regional_raster_cnn_cli \
    --input "$INPUT_CSV" \
    --output-prefix "$output_prefix" \
    --split-strategy own_ship \
    --epochs 12 \
    --batch-size 64 \
    --learning-rate 0.001 \
    --loss-type "$loss_type" \
    --torch-device auto
}

run_variant "weighted_bce"
run_variant "focal"

python /Users/seoki/Desktop/research/examples/summarize_regional_raster_cnn_nola_pooled_compare_61day.py
