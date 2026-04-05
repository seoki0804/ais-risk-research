#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-03-17_r24}"
SOURCE_RUN_DATE="${SOURCE_RUN_DATE:-2026-03-17_r23}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_true_new_area_savannah_pooled"
POOLED_CSV="${OUT_DIR}/savannah_pooled_pairwise.csv"
POOLED_SUMMARY="${OUT_DIR}/savannah_pooled_pairwise_summary.json"

usage() {
  cat <<'EOF'
Usage:
  SOURCE_RUN_DATE=2026-03-17_r23 run_true_new_area_savannah_pooled_61day.sh [RUN_DATE]

Description:
  Pool the current Savannah true-new-area pilot pairwise datasets
  (`2023-09-05`, `2023-09-06`, `2023-09-07`, `2023-09-08`) and run own_ship/timestamp
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
  python "${ROOT}/examples/build_true_new_area_savannah_pooled_61day.py" \
    --input "${ROOT}/outputs/${SOURCE_RUN_DATE}_true_new_area_savannah_20230905/savannah_true_extension_2023-09-05/savannah_pairwise_dataset.csv" \
    --input "${ROOT}/outputs/${SOURCE_RUN_DATE}_true_new_area_savannah_20230906/savannah_true_extension_2023-09-06/savannah_pairwise_dataset.csv" \
    --input "${ROOT}/outputs/${SOURCE_RUN_DATE}_true_new_area_savannah_20230907/savannah_true_extension_2023-09-07/savannah_pairwise_dataset.csv" \
    --input "${ROOT}/outputs/${SOURCE_RUN_DATE}_true_new_area_savannah_20230908/savannah_true_extension_2023-09-08/savannah_pairwise_dataset.csv" \
    --output "${POOLED_CSV}" \
    --summary-json "${POOLED_SUMMARY}"
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/savannah_pooled_${split}"
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
echo "own_ship_summary=${OUT_DIR}/savannah_pooled_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/savannah_pooled_timestamp_summary.json"
