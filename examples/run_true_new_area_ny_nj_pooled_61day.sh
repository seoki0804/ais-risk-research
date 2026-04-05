#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-03-17_r5}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_true_new_area_ny_nj_pooled"
POOLED_CSV="${OUT_DIR}/ny_nj_pooled_pairwise.csv"
POOLED_SUMMARY="${OUT_DIR}/ny_nj_pooled_pairwise_summary.json"

usage() {
  cat <<'EOF'
Usage:
  run_true_new_area_ny_nj_pooled_61day.sh [RUN_DATE]

Description:
  Pool the current NY/NJ true-new-area pilot pairwise datasets
  (`2023-09-01`, `2023-09-05`, `2023-10-08`) and run own_ship/timestamp
  hgbt/logreg benchmarks.
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${OUT_DIR}"

(
  cd "${ROOT}"
  python "${ROOT}/examples/build_true_new_area_ny_nj_pooled_61day.py" \
    --output "${POOLED_CSV}" \
    --summary-json "${POOLED_SUMMARY}"
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/ny_nj_pooled_${split}"
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
echo "own_ship_summary=${OUT_DIR}/ny_nj_pooled_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/ny_nj_pooled_timestamp_summary.json"
