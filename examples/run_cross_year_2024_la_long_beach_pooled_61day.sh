#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-04-05_r1}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_cross_year_2024_la_long_beach_pooled"
POOLED_CSV="${OUT_DIR}/la_long_beach_2024_pooled_pairwise.csv"
POOLED_SUMMARY="${OUT_DIR}/la_long_beach_2024_pooled_pairwise_summary.json"

INPUT_20240901="${INPUT_20240901_OVERRIDE:-${ROOT}/outputs/2026-03-17_r43_cross_year_2024_la_long_beach_pilot_20240901/la_long_beach_2024_20240901/la_long_beach_2024_pairwise_dataset.csv}"
INPUT_20240902="${INPUT_20240902_OVERRIDE:-${ROOT}/outputs/2026-03-17_r42_cross_year_2024_la_long_beach_pilot_20240902/la_long_beach_2024_20240902/la_long_beach_2024_pairwise_dataset.csv}"
INPUT_20241008="${INPUT_20241008_OVERRIDE:-${ROOT}/outputs/2026-03-17_r44_cross_year_2024_la_long_beach_pilot_20241008/la_long_beach_2024_20241008/la_long_beach_2024_pairwise_dataset.csv}"

usage() {
  cat <<'EOF'
Usage:
  run_cross_year_2024_la_long_beach_pooled_61day.sh [RUN_DATE]

Description:
  Build a three-date pooled LA/Long Beach 2024 pairwise CSV and run own_ship
  and timestamp hgbt/logreg benchmarks.
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

for path in "${INPUT_20240901}" "${INPUT_20240902}" "${INPUT_20241008}"; do
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
    --input "${INPUT_20240902}" \
    --input "${INPUT_20241008}" \
    --output "${POOLED_CSV}" \
    --summary-json "${POOLED_SUMMARY}"
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/la_long_beach_2024_pooled_${split}"
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
echo "pooled_summary=${POOLED_SUMMARY}"
echo "own_ship_summary=${OUT_DIR}/la_long_beach_2024_pooled_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/la_long_beach_2024_pooled_timestamp_summary.json"
