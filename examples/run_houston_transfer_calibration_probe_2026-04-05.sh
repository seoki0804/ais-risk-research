#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRANSFER_SCAN_DETAIL_CSV="${TRANSFER_SCAN_DETAIL_CSV:-${ROOT}/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan_detail.csv}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/houston_transfer_calibration_probe_2026-04-05_10seed}"
SOURCE_REGION="${SOURCE_REGION:-houston}"
MODELS="${MODELS:-rule_score,logreg,hgbt,random_forest,extra_trees,torch_mlp}"
METHODS="${METHODS:-none,platt,isotonic}"
THRESHOLD_GRID_STEP="${THRESHOLD_GRID_STEP:-0.01}"
ECE_GATE_MAX="${ECE_GATE_MAX:-0.10}"
MAX_NEGATIVE_PAIRS_ALLOWED="${MAX_NEGATIVE_PAIRS_ALLOWED:-1}"
RANDOM_SEED="${RANDOM_SEED:-42}"

(
  cd "${ROOT}"
  env PYTHONPATH=src python -m ais_risk.transfer_calibration_probe_cli \
    --transfer-scan-detail-csv "${TRANSFER_SCAN_DETAIL_CSV}" \
    --output-prefix "${OUTPUT_PREFIX}" \
    --source-region "${SOURCE_REGION}" \
    --models "${MODELS}" \
    --methods "${METHODS}" \
    --threshold-grid-step "${THRESHOLD_GRID_STEP}" \
    --ece-gate-max "${ECE_GATE_MAX}" \
    --max-negative-pairs-allowed "${MAX_NEGATIVE_PAIRS_ALLOWED}" \
    --random-seed "${RANDOM_SEED}"
)

echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
echo "detail_csv=${OUTPUT_PREFIX}_detail.csv"
echo "model_method_summary_csv=${OUTPUT_PREFIX}_model_method_summary.csv"

