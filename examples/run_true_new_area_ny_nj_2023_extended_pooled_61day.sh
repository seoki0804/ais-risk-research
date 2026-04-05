#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-04-05_r22_nynj_ext_overridepool}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_true_new_area_ny_nj_2023_extended_pooled"
POOLED_CSV="${OUT_DIR}/ny_nj_2023_extended_pooled_pairwise.csv"
POOLED_SUMMARY="${OUT_DIR}/ny_nj_2023_extended_pooled_pairwise_summary.json"

INPUT_20230901="${INPUT_20230901_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230901/ny_nj_true_extension_2023-09-01/ny_nj_pairwise_dataset.csv}"
INPUT_20230902="${INPUT_20230902_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230902/ny_nj_true_extension_2023-09-02/ny_nj_pairwise_dataset.csv}"
INPUT_20230903="${INPUT_20230903_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230903/ny_nj_true_extension_2023-09-03/ny_nj_pairwise_dataset.csv}"
INPUT_20230904="${INPUT_20230904_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230904/ny_nj_true_extension_2023-09-04/ny_nj_pairwise_dataset.csv}"
INPUT_20230905="${INPUT_20230905_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230905/ny_nj_true_extension_2023-09-05/ny_nj_pairwise_dataset.csv}"
INPUT_20230906="${INPUT_20230906_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230906/ny_nj_true_extension_2023-09-06/ny_nj_pairwise_dataset.csv}"
INPUT_20230907="${INPUT_20230907_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230907/ny_nj_true_extension_2023-09-07/ny_nj_pairwise_dataset.csv}"
INPUT_20230908="${INPUT_20230908_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230908/ny_nj_true_extension_2023-09-08/ny_nj_pairwise_dataset.csv}"
INPUT_20230909="${INPUT_20230909_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20230909/ny_nj_true_extension_2023-09-09/ny_nj_pairwise_dataset.csv}"
INPUT_20231008="${INPUT_20231008_OVERRIDE:-${ROOT}/outputs/2026-04-05_r21_nynj_override_true_new_area_ny_nj_20231008/ny_nj_true_extension_2023-10-08/ny_nj_pairwise_dataset.csv}"

usage() {
  cat <<'EOF'
Usage:
  run_true_new_area_ny_nj_2023_extended_pooled_61day.sh [RUN_DATE]

Description:
  Build an extended NY/NJ 2023 pooled pairwise set
  (2023-09-01..09, 10-08)
  and run own_ship/timestamp hgbt/logreg benchmarks.
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

for path in \
  "${INPUT_20230901}" "${INPUT_20230902}" "${INPUT_20230903}" \
  "${INPUT_20230904}" "${INPUT_20230905}" "${INPUT_20230906}" \
  "${INPUT_20230907}" "${INPUT_20230908}" "${INPUT_20230909}" \
  "${INPUT_20231008}"; do
  if [[ ! -f "${path}" ]]; then
    echo "error=missing_input path=${path}" >&2
    exit 1
  fi
done

mkdir -p "${OUT_DIR}"

(
  cd "${ROOT}"
  python "${ROOT}/examples/build_true_new_area_ny_nj_pooled_61day.py" \
    --input "${INPUT_20230901}" \
    --input "${INPUT_20230902}" \
    --input "${INPUT_20230903}" \
    --input "${INPUT_20230904}" \
    --input "${INPUT_20230905}" \
    --input "${INPUT_20230906}" \
    --input "${INPUT_20230907}" \
    --input "${INPUT_20230908}" \
    --input "${INPUT_20230909}" \
    --input "${INPUT_20231008}" \
    --output "${POOLED_CSV}" \
    --summary-json "${POOLED_SUMMARY}"
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/ny_nj_2023_extended_pooled_${split}"
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
echo "own_ship_summary=${OUT_DIR}/ny_nj_2023_extended_pooled_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/ny_nj_2023_extended_pooled_timestamp_summary.json"
