#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${RUN_DATE:-2026-03-17_r36}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_cross_year_ny_nj_transfer"
TRAIN_2023="${TRAIN_2023_OVERRIDE:-${ROOT}/outputs/2026-03-17_r5_true_new_area_ny_nj_pooled/ny_nj_pooled_pairwise.csv}"
TRAIN_2024="${TRAIN_2024_OVERRIDE:-${ROOT}/outputs/2026-03-17_r35_cross_year_2024_ny_nj_pooled/ny_nj_2024_pooled_pairwise.csv}"
export PYTHONPATH="${ROOT}/src"

usage() {
  cat <<'EOF'
Usage:
  run_cross_year_ny_nj_transfer_61day.sh

Description:
  Run pooled NY/NJ cross-year transfer in both directions:
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

run_transfer "ny_nj_2023_to_2024" "${TRAIN_2023}" "${TRAIN_2024}"
run_transfer "ny_nj_2024_to_2023" "${TRAIN_2024}" "${TRAIN_2023}"

python "${ROOT}/examples/summarize_cross_year_ny_nj_transfer_61day.py" \
  --run-root "${OUT_DIR}" \
  --output-md "${ROOT}/outputs/presentation_deck_outline_61day_2026-03-13/cross_year_ny_nj_transfer_note_61day.md" \
  --output-csv "${ROOT}/outputs/presentation_deck_outline_61day_2026-03-13/cross_year_ny_nj_transfer_summary_61day.csv"

echo "run_root=${OUT_DIR}"
