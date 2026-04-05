#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
export PYTHONPATH="${ROOT}/src"

BASE_POOLED_DIR="${BASE_POOLED_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
OUT_HOU="${OUT_HOU:-${ROOT}/outputs/2026-03-19_houston_cleaned_input_control_leakfix}"
OUT_SEA="${OUT_SEA:-${ROOT}/outputs/2026-03-19_seattle_cleaned_input_control_leakfix}"
OUT_NOLA="${OUT_NOLA:-${ROOT}/outputs/2026-03-19_nola_cleaned_input_control_leakfix}"

run_cmd() {
  if [[ "${PRINT_ONLY:-0}" == "1" ]]; then
    printf '%s\n' "$*"
  else
    eval "$@"
  fi
}

mkdir -p "${OUT_HOU}" "${OUT_SEA}" "${OUT_NOLA}"

run_cmd "python ${ROOT}/examples/build_cleaned_input_control_61day.py \
  --input ${BASE_POOLED_DIR}/houston_pooled_pairwise.csv \
  --output ${OUT_HOU}/houston_pooled_observed_pair.csv \
  --mode observed_pair \
  --summary-json ${OUT_HOU}/houston_pooled_observed_pair_filter_summary.json"

run_cmd "python ${ROOT}/examples/build_cleaned_input_control_61day.py \
  --input ${BASE_POOLED_DIR}/seattle_pooled_pairwise.csv \
  --output ${OUT_SEA}/seattle_pooled_observed_pair.csv \
  --mode observed_pair \
  --summary-json ${OUT_SEA}/seattle_pooled_observed_pair_filter_summary.json"

run_cmd "python ${ROOT}/examples/build_cleaned_input_control_61day.py \
  --input ${BASE_POOLED_DIR}/nola_pooled_pairwise.csv \
  --output ${OUT_NOLA}/nola_pooled_observed_pair.csv \
  --mode observed_pair \
  --summary-json ${OUT_NOLA}/nola_pooled_observed_pair_filter_summary.json"

run_cmd "python -m ais_risk.benchmark_cli \
  --input ${OUT_HOU}/houston_pooled_observed_pair.csv \
  --output-prefix ${OUT_HOU}/houston_pooled_observed_pair_hgbt \
  --split-strategy own_ship \
  --models logreg,hgbt"

run_cmd "python -m ais_risk.benchmark_cli \
  --input ${OUT_HOU}/houston_pooled_observed_pair.csv \
  --output-prefix ${OUT_HOU}/houston_pooled_observed_pair_timestamp \
  --split-strategy timestamp \
  --models logreg,hgbt"

run_cmd "python -m ais_risk.regional_raster_cnn_cli \
  --input ${OUT_HOU}/houston_pooled_observed_pair.csv \
  --output-prefix ${OUT_HOU}/houston_pooled_observed_pair_timestamp_cnn_weighted \
  --split-strategy timestamp \
  --epochs 12 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --loss-type weighted_bce \
  --torch-device auto"

run_cmd "python -m ais_risk.benchmark_cli \
  --input ${OUT_SEA}/seattle_pooled_observed_pair.csv \
  --output-prefix ${OUT_SEA}/seattle_pooled_observed_pair_hgbt \
  --split-strategy own_ship \
  --models logreg,hgbt"

run_cmd "python -m ais_risk.regional_raster_cnn_cli \
  --input ${OUT_SEA}/seattle_pooled_observed_pair.csv \
  --output-prefix ${OUT_SEA}/seattle_pooled_observed_pair_cnn_weighted \
  --split-strategy own_ship \
  --epochs 12 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --loss-type weighted_bce \
  --torch-device auto"

run_cmd "python -m ais_risk.benchmark_cli \
  --input ${OUT_NOLA}/nola_pooled_observed_pair.csv \
  --output-prefix ${OUT_NOLA}/nola_pooled_observed_pair_hgbt \
  --split-strategy own_ship \
  --models logreg,hgbt"

run_cmd "python -m ais_risk.regional_raster_cnn_cli \
  --input ${OUT_NOLA}/nola_pooled_observed_pair.csv \
  --output-prefix ${OUT_NOLA}/nola_pooled_observed_pair_cnn_weighted \
  --split-strategy own_ship \
  --epochs 12 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --loss-type weighted_bce \
  --torch-device auto"

run_cmd "python ${ROOT}/examples/summarize_cleaned_input_control_multiarea_61day.py"
