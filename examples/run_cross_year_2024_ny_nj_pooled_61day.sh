#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-03-17_r33}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_cross_year_2024_ny_nj_pooled"
POOLED_CSV="${OUT_DIR}/ny_nj_2024_pooled_pairwise.csv"
POOLED_SUMMARY="${OUT_DIR}/ny_nj_2024_pooled_pairwise_summary.json"

INPUT_20240901="${INPUT_20240901_OVERRIDE:-${ROOT}/outputs/2026-03-17_r32_cross_year_2024_ny_nj_pilot_20240901/ny_nj_2024_20240901/ny_nj_2024_pairwise_dataset.csv}"
INPUT_20240905="${INPUT_20240905_OVERRIDE:-${ROOT}/outputs/2026-03-17_r28_cross_year_2024_ny_nj_pilot_20240905/ny_nj_2024_20240905/ny_nj_2024_pairwise_dataset.csv}"
INPUT_20241008="${INPUT_20241008_OVERRIDE:-${ROOT}/outputs/2026-03-17_r30_cross_year_2024_ny_nj_pilot_20241008/ny_nj_2024_20241008/ny_nj_2024_pairwise_dataset.csv}"

usage() {
  cat <<'EOF'
Usage:
  run_cross_year_2024_ny_nj_pooled_61day.sh [RUN_DATE]

Description:
  Pool the current three NY/NJ 2024 same-day pairwise pilots
  (`2024-09-01`, `2024-09-05`, `2024-10-08`) and run own_ship/timestamp
  hgbt/logreg benchmarks.
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

for path in "${INPUT_20240901}" "${INPUT_20240905}" "${INPUT_20241008}"; do
  if [[ ! -f "${path}" ]]; then
    echo "error=missing_input path=${path}" >&2
    exit 1
  fi
done

mkdir -p "${OUT_DIR}"

(
  cd "${ROOT}"
  python "${ROOT}/examples/build_true_new_area_ny_nj_pooled_61day.py" \
    --input "${INPUT_20240901}" \
    --input "${INPUT_20240905}" \
    --input "${INPUT_20241008}" \
    --output "${POOLED_CSV}" \
    --summary-json "${POOLED_SUMMARY}"
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/ny_nj_2024_pooled_${split}"
  echo "benchmark_split=${split} output_prefix=${out_prefix}"
  (
    cd "${ROOT}"
    PYTHONPATH=src python -m ais_risk.benchmark_cli \
      --input "${POOLED_CSV}" \
      --output-prefix "${out_prefix}" \
      --models hgbt,logreg \
      --split-strategy "${split}"
  )
done

echo "pooled_csv=${POOLED_CSV}"
echo "own_ship_summary=${OUT_DIR}/ny_nj_2024_pooled_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/ny_nj_2024_pooled_timestamp_summary.json"
