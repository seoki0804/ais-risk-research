#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src"

BASE_DIR="${BASE_DIR:-/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
INPUT_CSV="${INPUT_CSV:-$BASE_DIR/nola_pooled_pairwise.csv}"
OUTPUT_DIR="${OUTPUT_DIR:-/Users/seoki/Desktop/research/outputs/2026-03-19_nola_cleaned_input_control_leakfix}"
FILTERED_CSV="$OUTPUT_DIR/nola_pooled_observed_pair.csv"
FILTER_SUMMARY="$OUTPUT_DIR/nola_pooled_observed_pair_filter_summary.json"
HGBT_PREFIX="$OUTPUT_DIR/nola_pooled_observed_pair_hgbt"
CNN_PREFIX="$OUTPUT_DIR/nola_pooled_observed_pair_cnn_weighted"

mkdir -p "$OUTPUT_DIR"

python /Users/seoki/Desktop/research/examples/build_cleaned_input_control_61day.py \
  --input "$INPUT_CSV" \
  --output "$FILTERED_CSV" \
  --mode observed_pair \
  --summary-json "$FILTER_SUMMARY"

python -m ais_risk.benchmark_cli \
  --input "$FILTERED_CSV" \
  --output-prefix "$HGBT_PREFIX" \
  --split-strategy own_ship \
  --models logreg,hgbt

python -m ais_risk.regional_raster_cnn_cli \
  --input "$FILTERED_CSV" \
  --output-prefix "$CNN_PREFIX" \
  --split-strategy own_ship \
  --epochs 12 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --loss-type weighted_bce \
  --torch-device auto

python /Users/seoki/Desktop/research/examples/summarize_nola_cleaned_input_control_61day.py
