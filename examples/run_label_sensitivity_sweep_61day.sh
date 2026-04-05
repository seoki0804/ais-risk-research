#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="/Users/seoki/Desktop/research"
PYTHONPATH_VALUE="${ROOT_DIR}/src"

PRINT_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --print-only)
      PRINT_ONLY=1
      shift
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -lt 3 ]]; then
  echo "usage: run_label_sensitivity_sweep_61day.sh [--print-only] <manifest> <raw_input> <output_root>" >&2
  exit 1
fi

MANIFEST="$1"
RAW_INPUT="$2"
OUTPUT_ROOT="$3"

LABELS=("0.3" "0.5" "0.8" "1.0" "1.6")
CONFIGS=(
  "/Users/seoki/Desktop/research/configs/base_horizon10.toml"
  "/Users/seoki/Desktop/research/configs/base.toml"
  "/Users/seoki/Desktop/research/configs/base_horizon20.toml"
)

run_one() {
  local config_path="$1"
  local label_distance="$2"
  local horizon_tag
  local output_dir
  local cmd

  horizon_tag="$(basename "${config_path}" .toml)"
  output_dir="${OUTPUT_ROOT}/${horizon_tag}_label_${label_distance//./p}"

  cmd=(
    python -m ais_risk.study_run_cli
    --manifest "${MANIFEST}"
    --raw-input "${RAW_INPUT}"
    --config "${config_path}"
    --output-root "${output_dir}"
    --pairwise-label-distance-nm "${label_distance}"
    --pairwise-split-strategy own_ship
    --benchmark-models "rule_score,logreg,hgbt"
    --run-own-ship-loo
    --run-own-ship-case-eval
    --own-ship-case-eval-repeat-count 7
    --run-calibration-eval
    --random-seed 42
  )

  if [[ "${PRINT_ONLY}" -eq 1 ]]; then
    printf 'PYTHONPATH=%q ' "${PYTHONPATH_VALUE}"
    printf '%q ' "${cmd[@]}"
    printf '\n'
  else
    PYTHONPATH="${PYTHONPATH_VALUE}" "${cmd[@]}"
  fi
}

for config_path in "${CONFIGS[@]}"; do
  for label_distance in "${LABELS[@]}"; do
    run_one "${config_path}" "${label_distance}"
  done
done
