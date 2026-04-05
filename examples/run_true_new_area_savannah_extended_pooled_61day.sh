#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-04-05_r13}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_true_new_area_savannah_extended_pooled"
POOLED_CSV="${OUT_DIR}/savannah_extended_pooled_pairwise.csv"
POOLED_SUMMARY="${OUT_DIR}/savannah_extended_pooled_pairwise_summary.json"

INPUT_20230902="${INPUT_20230902_OVERRIDE:-${ROOT}/outputs/2026-04-05_r15_sav_override_true_new_area_savannah_20230902/savannah_true_extension_2023-09-02/savannah_pairwise_dataset.csv}"
INPUT_20230905="${INPUT_20230905_OVERRIDE:-${ROOT}/outputs/2026-03-17_r23_true_new_area_savannah_20230905/savannah_true_extension_2023-09-05/savannah_pairwise_dataset.csv}"
INPUT_20230906="${INPUT_20230906_OVERRIDE:-${ROOT}/outputs/2026-04-05_r15_sav_override_true_new_area_savannah_20230906/savannah_true_extension_2023-09-06/savannah_pairwise_dataset.csv}"
INPUT_20230907="${INPUT_20230907_OVERRIDE:-${ROOT}/outputs/2026-04-05_r15_sav_override_true_new_area_savannah_20230907/savannah_true_extension_2023-09-07/savannah_pairwise_dataset.csv}"
INPUT_20230908="${INPUT_20230908_OVERRIDE:-${ROOT}/outputs/2026-04-05_r15_sav_override_true_new_area_savannah_20230908/savannah_true_extension_2023-09-08/savannah_pairwise_dataset.csv}"
INPUT_20230909="${INPUT_20230909_OVERRIDE:-${ROOT}/outputs/2026-04-05_r15_sav_override_true_new_area_savannah_20230909/savannah_true_extension_2023-09-09/savannah_pairwise_dataset.csv}"

usage() {
  cat <<'EOF'
Usage:
  run_true_new_area_savannah_extended_pooled_61day.sh [RUN_DATE]

Description:
  Build Savannah extended pooled pairwise set
  (2023-09-02, 09-05, 09-06, 09-07, 09-08, 09-09)
  using override-enriched pilot bundles where available
  and run own_ship/timestamp hgbt/logreg benchmarks.
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

for path in \
  "${INPUT_20230902}" "${INPUT_20230905}" "${INPUT_20230906}" \
  "${INPUT_20230907}" "${INPUT_20230908}" "${INPUT_20230909}"; do
  if [[ ! -f "${path}" ]]; then
    echo "error=missing_input path=${path}" >&2
    exit 1
  fi
done

mkdir -p "${OUT_DIR}"

(
  cd "${ROOT}"
  python "${ROOT}/examples/build_true_new_area_savannah_pooled_61day.py" \
    --input "${INPUT_20230902}" \
    --input "${INPUT_20230905}" \
    --input "${INPUT_20230906}" \
    --input "${INPUT_20230907}" \
    --input "${INPUT_20230908}" \
    --input "${INPUT_20230909}" \
    --output "${POOLED_CSV}" \
    --summary-json "${POOLED_SUMMARY}"
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/savannah_extended_pooled_${split}"
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
echo "own_ship_summary=${OUT_DIR}/savannah_extended_pooled_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/savannah_extended_pooled_timestamp_summary.json"
