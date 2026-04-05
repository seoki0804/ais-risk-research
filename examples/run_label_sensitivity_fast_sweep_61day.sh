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
  echo "usage: run_label_sensitivity_fast_sweep_61day.sh [--print-only] <tracks_csv> <output_root> <candidates_csv>" >&2
  exit 1
fi

TRACKS_CSV="$1"
OUTPUT_ROOT="$2"
CANDIDATES_CSV="$3"

LABELS=("0.3" "0.5" "0.8" "1.0" "1.6")
CONFIGS=(
  "/Users/seoki/Desktop/research/configs/base_horizon10.toml"
  "/Users/seoki/Desktop/research/configs/base.toml"
  "/Users/seoki/Desktop/research/configs/base_horizon20.toml"
)

run_cmd() {
  if [[ "${PRINT_ONLY}" -eq 1 ]]; then
    printf 'PYTHONPATH=%q ' "${PYTHONPATH_VALUE}"
    printf '%q ' "$@"
    printf '\n'
  else
    PYTHONPATH="${PYTHONPATH_VALUE}" "$@"
  fi
}

for config_path in "${CONFIGS[@]}"; do
  horizon_tag="$(basename "${config_path}" .toml)"
  for label_distance in "${LABELS[@]}"; do
    run_name="${horizon_tag}_label_${label_distance//./p}"
    run_dir="${OUTPUT_ROOT}/${run_name}"
    mkdir -p "${run_dir}"

    pairwise_csv="${run_dir}/pairwise_dataset.csv"
    pairwise_stats="${run_dir}/pairwise_dataset_stats.json"
    benchmark_prefix="${run_dir}/benchmark"
    loo_prefix="${run_dir}/own_ship_loo"
    case_prefix="${run_dir}/own_ship_case"
    cal_prefix="${run_dir}/calibration"

    run_cmd python -m ais_risk.pairwise_dataset_cli \
      --input "${TRACKS_CSV}" \
      --config "${config_path}" \
      --output "${pairwise_csv}" \
      --stats-output "${pairwise_stats}" \
      --own-candidates "${CANDIDATES_CSV}" \
      --top-n-candidates 5 \
      --label-distance-nm "${label_distance}" \
      --sample-every 1 \
      --min-future-points 2 \
      --min-targets 1

    run_cmd python -m ais_risk.benchmark_cli \
      --input "${pairwise_csv}" \
      --output-prefix "${benchmark_prefix}" \
      --models "rule_score,logreg,hgbt" \
      --split-strategy own_ship \
      --random-seed 42

    run_cmd python -m ais_risk.own_ship_cv_cli \
      --input "${pairwise_csv}" \
      --output-prefix "${loo_prefix}" \
      --models "rule_score,logreg,hgbt" \
      --val-fraction 0.2 \
      --random-seed 42

    run_cmd python -m ais_risk.own_ship_case_eval_cli \
      --input "${pairwise_csv}" \
      --output-prefix "${case_prefix}" \
      --models "rule_score,logreg,hgbt" \
      --min-rows-per-ship 30 \
      --train-fraction 0.6 \
      --val-fraction 0.2 \
      --repeat-count 7 \
      --random-seed 42

    run_cmd python -m ais_risk.calibration_eval_cli \
      --predictions "${benchmark_prefix}_test_predictions.csv" \
      --output-prefix "${cal_prefix}" \
      --models "rule_score,logreg,hgbt" \
      --num-bins 10
  done
done
