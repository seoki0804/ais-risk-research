#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_CSV="${INPUT_CSV:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix/houston_pooled_pairwise.csv}"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT}/outputs/all_models_houston_2026-03-28}"
SPLIT_STRATEGY="${SPLIT_STRATEGY:-own_ship}"
TORCH_DEVICE="${TORCH_DEVICE:-auto}"
INCLUDE_CNN="${INCLUDE_CNN:-0}"
AUTO_ADJUST_SPLIT="${AUTO_ADJUST_SPLIT:-1}"

cmd=(
  python -m ais_risk.all_models_cli
  --input "${INPUT_CSV}"
  --output-dir "${OUTPUT_DIR}"
  --split-strategy "${SPLIT_STRATEGY}"
  --torch-device "${TORCH_DEVICE}"
)

if [[ "${INCLUDE_CNN}" == "1" ]]; then
  cmd+=(--include-regional-cnn --cnn-losses "weighted_bce,focal")
fi
if [[ "${AUTO_ADJUST_SPLIT}" == "1" ]]; then
  cmd+=(--auto-adjust-split-for-support)
fi

(
  cd "${ROOT}"
  PYTHONPATH=src "${cmd[@]}"
)
