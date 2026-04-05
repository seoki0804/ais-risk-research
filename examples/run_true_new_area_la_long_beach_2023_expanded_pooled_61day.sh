#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-04-05_r14}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_true_new_area_la_long_beach_2023_expanded_pooled"
POOLED_CSV="${OUT_DIR}/la_long_beach_2023_expanded_pooled_pairwise.csv"
POOLED_SUMMARY="${OUT_DIR}/la_long_beach_2023_expanded_pooled_pairwise_summary.json"

INPUT_20230901="${INPUT_20230901_OVERRIDE:-${ROOT}/outputs/2026-03-19_r2_lalb2023_true_new_area_la_long_beach_20230901/la_long_beach_true_extension_2023-09-01/la_long_beach_pairwise_dataset.csv}"
INPUT_20230902="${INPUT_20230902_OVERRIDE:-${ROOT}/outputs/2026-04-05_r16_lalb_override_true_new_area_la_long_beach_20230902/la_long_beach_true_extension_2023-09-02/la_long_beach_pairwise_dataset.csv}"
INPUT_20230903="${INPUT_20230903_OVERRIDE:-${ROOT}/outputs/2026-04-05_r3_lalb2023ext_true_new_area_la_long_beach_20230903/la_long_beach_true_extension_2023-09-03/la_long_beach_pairwise_dataset.csv}"
INPUT_20230904="${INPUT_20230904_OVERRIDE:-${ROOT}/outputs/2026-04-05_r3_lalb2023ext_true_new_area_la_long_beach_20230904/la_long_beach_true_extension_2023-09-04/la_long_beach_pairwise_dataset.csv}"
INPUT_20230905="${INPUT_20230905_OVERRIDE:-${ROOT}/outputs/2026-03-19_r2_lalb2023_true_new_area_la_long_beach_20230905/la_long_beach_true_extension_2023-09-05/la_long_beach_pairwise_dataset.csv}"
INPUT_20230906="${INPUT_20230906_OVERRIDE:-${ROOT}/outputs/2026-04-05_r16_lalb_override_true_new_area_la_long_beach_20230906/la_long_beach_true_extension_2023-09-06/la_long_beach_pairwise_dataset.csv}"
INPUT_20230907="${INPUT_20230907_OVERRIDE:-${ROOT}/outputs/2026-04-05_r16_lalb_override_true_new_area_la_long_beach_20230907/la_long_beach_true_extension_2023-09-07/la_long_beach_pairwise_dataset.csv}"
INPUT_20230908="${INPUT_20230908_OVERRIDE:-${ROOT}/outputs/2026-04-05_r16_lalb_override_true_new_area_la_long_beach_20230908/la_long_beach_true_extension_2023-09-08/la_long_beach_pairwise_dataset.csv}"
INPUT_20230909="${INPUT_20230909_OVERRIDE:-${ROOT}/outputs/2026-04-05_r16_lalb_override_true_new_area_la_long_beach_20230909/la_long_beach_true_extension_2023-09-09/la_long_beach_pairwise_dataset.csv}"
INPUT_20231008="${INPUT_20231008_OVERRIDE:-${ROOT}/outputs/2026-03-17_r8_true_new_area_la_long_beach_20231008/la_long_beach_true_extension_2023-10-08/la_long_beach_pairwise_dataset.csv}"

usage() {
  cat <<'EOF'
Usage:
  run_true_new_area_la_long_beach_2023_expanded_pooled_61day.sh [RUN_DATE]

Description:
  Build LA/Long Beach 2023 expanded pooled pairwise set
  (2023-09-01..09, 10-08 subset available in this repo),
  using override-enriched pilot bundles where available.
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
  python "${ROOT}/examples/build_true_new_area_la_long_beach_pooled_61day.py" \
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
  out_prefix="${OUT_DIR}/la_long_beach_2023_expanded_pooled_${split}"
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
echo "own_ship_summary=${OUT_DIR}/la_long_beach_2023_expanded_pooled_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/la_long_beach_2023_expanded_pooled_timestamp_summary.json"
