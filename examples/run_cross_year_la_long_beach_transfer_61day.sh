#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${RUN_DATE:-2026-04-05_r2}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_cross_year_la_long_beach_transfer"
TRAIN_2023="${TRAIN_2023_OVERRIDE:-${ROOT}/outputs/2026-03-17_r13_true_new_area_la_long_beach_pooled/la_long_beach_pooled_pairwise.csv}"
TRAIN_2024="${TRAIN_2024_OVERRIDE:-${ROOT}/outputs/2026-04-05_r1_cross_year_2024_la_long_beach_pooled/la_long_beach_2024_pooled_pairwise.csv}"
export PYTHONPATH="${ROOT}/src"

usage() {
  cat <<'EOF'
Usage:
  run_cross_year_la_long_beach_transfer_61day.sh

Description:
  Run pooled LA/Long Beach cross-year transfer in both directions:
  - 2023 pooled -> 2024 pooled
  - 2024 pooled -> 2023 pooled
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

for path in "${TRAIN_2023}" "${TRAIN_2024}"; do
  if [[ ! -f "${path}" ]]; then
    echo "error=missing_input path=${path}" >&2
    exit 1
  fi
done

mkdir -p "${OUT_DIR}"

run_transfer() {
  local label="$1"
  local train_input="$2"
  local target_input="$3"
  local prefix="${OUT_DIR}/${label}"
  (
    cd "${ROOT}"
    python -m ais_risk.benchmark_transfer_cli \
      --train-input "${train_input}" \
      --target-input "${target_input}" \
      --output-prefix "${prefix}" \
      --models hgbt,logreg \
      --split-strategy own_ship
  )
}

run_transfer "la_long_beach_2023_to_2024" "${TRAIN_2023}" "${TRAIN_2024}"
run_transfer "la_long_beach_2024_to_2023" "${TRAIN_2024}" "${TRAIN_2023}"

echo "run_root=${OUT_DIR}"
echo "transfer_2023_to_2024=${OUT_DIR}/la_long_beach_2023_to_2024_transfer_summary.json"
echo "transfer_2024_to_2023=${OUT_DIR}/la_long_beach_2024_to_2023_transfer_summary.json"
