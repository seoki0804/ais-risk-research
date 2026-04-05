#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${RUN_DATE:-2026-03-17}"
MAINLABEL_RUN_DATE="${MAINLABEL_RUN_DATE:-2026-03-17}"
OUT_ROOT="${ROOT}/outputs/${RUN_DATE}_same_ecosystem_external_validity"
export PYTHONPATH="${ROOT}/src"

REGIONS=(houston nola seattle)
BLOCK_NAMES=(aug sep oct)
AUG_DATES=("2023-08-08" "2023-08-09")
SEP_DATES=("2023-09-01" "2023-09-05")
OCT_DATES=("2023-10-08" "2023-10-09")

run_cmd() {
  if [[ "${PRINT_ONLY:-0}" == "1" ]]; then
    printf '%s\n' "$*"
  else
    eval "$@"
  fi
}

block_dates() {
  local block="$1"
  case "$block" in
    aug) printf '%s\n' "${AUG_DATES[@]}" ;;
    sep) printf '%s\n' "${SEP_DATES[@]}" ;;
    oct) printf '%s\n' "${OCT_DATES[@]}" ;;
    *)
      echo "error=unknown_block value=${block}" >&2
      exit 1
      ;;
  esac
}

build_pool() {
  local region="$1"
  local block="$2"
  local pooled_csv="${OUT_ROOT}/${region}_${block}_pooled_pairwise.csv"
  local summary_json="${OUT_ROOT}/${region}_${block}_pooled_summary.json"
  local dates
  dates="$(block_dates "$block" | tr '\n' ' ')"
  run_cmd "python ${ROOT}/examples/build_same_area_pooled_pairwise_61day.py \
    --region ${region} \
    --run-date ${MAINLABEL_RUN_DATE} \
    --dates ${dates} \
    --output ${pooled_csv} \
    --summary-json ${summary_json}"
}

run_transfer() {
  local region="$1"
  local source_block="$2"
  local target_block="$3"
  local prefix="${OUT_ROOT}/${region}_${source_block}_to_${target_block}"
  run_cmd "python -m ais_risk.benchmark_transfer_cli \
    --train-input ${OUT_ROOT}/${region}_${source_block}_pooled_pairwise.csv \
    --target-input ${OUT_ROOT}/${region}_${target_block}_pooled_pairwise.csv \
    --output-prefix ${prefix} \
    --models hgbt,logreg \
    --split-strategy own_ship"
}

mkdir -p "${OUT_ROOT}"

for region in "${REGIONS[@]}"; do
  for block in "${BLOCK_NAMES[@]}"; do
    build_pool "${region}" "${block}"
  done
  run_transfer "${region}" "aug" "sep"
  run_transfer "${region}" "aug" "oct"
  run_transfer "${region}" "sep" "oct"
done

run_cmd "python ${ROOT}/examples/summarize_same_ecosystem_external_validity_61day.py \
  --run-date ${RUN_DATE}"
