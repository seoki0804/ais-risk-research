#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
export PYTHONPATH="${ROOT}/src"

BASE_INPUT="${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-17/houston_pooled_pairwise.csv"
OUT_DIR="${ROOT}/outputs/2026-03-17_houston_relaxed_cleaned_input_control"

run_cmd() {
  if [[ "${PRINT_ONLY:-0}" == "1" ]]; then
    printf '%s\n' "$*"
  else
    eval "$@"
  fi
}

mkdir -p "${OUT_DIR}"

run_cmd "python ${ROOT}/examples/build_cleaned_input_control_61day.py \
  --input ${BASE_INPUT} \
  --output ${OUT_DIR}/houston_pooled_own_observed_allow_target_interp.csv \
  --mode own_observed_allow_target_interp \
  --summary-json ${OUT_DIR}/houston_pooled_own_observed_allow_target_interp_filter_summary.json"

run_cmd "python -m ais_risk.benchmark_cli \
  --input ${OUT_DIR}/houston_pooled_own_observed_allow_target_interp.csv \
  --output-prefix ${OUT_DIR}/houston_pooled_own_observed_allow_target_interp_own_ship \
  --split-strategy own_ship \
  --models logreg,hgbt"

run_cmd "python -m ais_risk.benchmark_cli \
  --input ${OUT_DIR}/houston_pooled_own_observed_allow_target_interp.csv \
  --output-prefix ${OUT_DIR}/houston_pooled_own_observed_allow_target_interp_timestamp \
  --split-strategy timestamp \
  --models logreg,hgbt"

run_cmd "python -m ais_risk.regional_raster_cnn_cli \
  --input ${OUT_DIR}/houston_pooled_own_observed_allow_target_interp.csv \
  --output-prefix ${OUT_DIR}/houston_pooled_own_observed_allow_target_interp_timestamp_cnn_weighted \
  --split-strategy timestamp \
  --epochs 12 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --loss-type weighted_bce \
  --torch-device auto"

run_cmd "python ${ROOT}/examples/summarize_houston_relaxed_cleaned_profile_61day.py"
