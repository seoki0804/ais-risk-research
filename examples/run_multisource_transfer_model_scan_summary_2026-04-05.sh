#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${ROOT}/outputs/2026-04-05_transfer_model_scan_multisource_10seed}"
SUMMARY_PREFIX="${SUMMARY_PREFIX:-${ROOT}/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed}"
MODELS="${MODELS:-rule_score,logreg,hgbt,random_forest,extra_trees,torch_mlp}"
THRESHOLD_GRID_STEP="${THRESHOLD_GRID_STEP:-0.01}"
RANDOM_SEED="${RANDOM_SEED:-42}"
MAX_TARGET_ECE="${MAX_TARGET_ECE:-0.10}"
MAX_NEGATIVE_PAIRS="${MAX_NEGATIVE_PAIRS:-1}"

mkdir -p "${OUTPUT_ROOT}"

run_scan() {
  local source_region="$1"
  local targets="$2"
  env PYTHONPATH=src python -m ais_risk.transfer_model_scan_cli \
    --source-region "${source_region}" \
    --source-input "${INPUT_DIR}/${source_region}_pooled_pairwise.csv" \
    --targets "${targets}" \
    --models "${MODELS}" \
    --output-root "${OUTPUT_ROOT}" \
    --split-strategy "own_ship" \
    --threshold-grid-step "${THRESHOLD_GRID_STEP}" \
    --random-seed "${RANDOM_SEED}" \
    --calibration-ece-max "${MAX_TARGET_ECE}"
}

(
  cd "${ROOT}"
  run_scan "houston" "nola:${INPUT_DIR}/nola_pooled_pairwise.csv,seattle:${INPUT_DIR}/seattle_pooled_pairwise.csv"
  run_scan "nola" "houston:${INPUT_DIR}/houston_pooled_pairwise.csv,seattle:${INPUT_DIR}/seattle_pooled_pairwise.csv"
  run_scan "seattle" "houston:${INPUT_DIR}/houston_pooled_pairwise.csv,nola:${INPUT_DIR}/nola_pooled_pairwise.csv"

  env PYTHONPATH=src python -m ais_risk.multisource_transfer_model_scan_summary_cli \
    --scan-output-root "${OUTPUT_ROOT}" \
    --source-regions "houston,nola,seattle" \
    --output-prefix "${SUMMARY_PREFIX}" \
    --max-target-ece "${MAX_TARGET_ECE}" \
    --max-negative-pairs "${MAX_NEGATIVE_PAIRS}"
)

echo "summary_md=${SUMMARY_PREFIX}.md"
echo "summary_json=${SUMMARY_PREFIX}.json"
echo "detail_csv=${SUMMARY_PREFIX}_detail.csv"
echo "source_summary_csv=${SUMMARY_PREFIX}_source_summary.csv"
