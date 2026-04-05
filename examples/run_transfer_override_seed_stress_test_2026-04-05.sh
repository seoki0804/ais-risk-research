#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/transfer_override_seed_stress_test_2026-04-05_10seed}"
SOURCE_REGION="${SOURCE_REGION:-houston}"
TARGET_REGIONS="${TARGET_REGIONS:-nola,seattle}"
BASELINE_MODEL="${BASELINE_MODEL:-hgbt}"
OVERRIDE_MODEL="${OVERRIDE_MODEL:-rule_score}"
OVERRIDE_METHOD="${OVERRIDE_METHOD:-isotonic}"
SEEDS="${SEEDS:-41,42,43,44,45}"
SPLIT_STRATEGY="${SPLIT_STRATEGY:-own_ship}"
TRAIN_FRACTION="${TRAIN_FRACTION:-0.6}"
VAL_FRACTION="${VAL_FRACTION:-0.2}"
THRESHOLD_GRID_STEP="${THRESHOLD_GRID_STEP:-0.01}"
ECE_GATE_MAX="${ECE_GATE_MAX:-0.10}"
MAX_NEGATIVE_PAIRS_ALLOWED="${MAX_NEGATIVE_PAIRS_ALLOWED:-1}"
TORCH_DEVICE="${TORCH_DEVICE:-auto}"
CALIBRATION_BINS="${CALIBRATION_BINS:-10}"

(
  cd "${ROOT}"
  env PYTHONPATH=src python -m ais_risk.transfer_override_seed_stress_test_cli \
    --input-dir "${INPUT_DIR}" \
    --output-prefix "${OUTPUT_PREFIX}" \
    --source-region "${SOURCE_REGION}" \
    --target-regions "${TARGET_REGIONS}" \
    --baseline-model "${BASELINE_MODEL}" \
    --override-model "${OVERRIDE_MODEL}" \
    --override-method "${OVERRIDE_METHOD}" \
    --seeds "${SEEDS}" \
    --split-strategy "${SPLIT_STRATEGY}" \
    --train-fraction "${TRAIN_FRACTION}" \
    --val-fraction "${VAL_FRACTION}" \
    --threshold-grid-step "${THRESHOLD_GRID_STEP}" \
    --ece-gate-max "${ECE_GATE_MAX}" \
    --max-negative-pairs-allowed "${MAX_NEGATIVE_PAIRS_ALLOWED}" \
    --torch-device "${TORCH_DEVICE}" \
    --calibration-bins "${CALIBRATION_BINS}"
)

echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
echo "per_seed_csv=${OUTPUT_PREFIX}_per_seed.csv"

