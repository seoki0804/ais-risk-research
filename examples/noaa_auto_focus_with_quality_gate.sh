#!/usr/bin/env bash
set -euo pipefail

# Example wrapper for auto-selected rotating own-ship validation with quality gate.
# Usage:
#   DATASET_ID=noaa_us_coastal_all_2023-08-01_2023-08-01_v1 \
#   RAW_INPUT=data/raw/noaa/noaa_us_coastal_all_2023-08-01_2023-08-01_v1/raw.csv \
#   ./examples/noaa_auto_focus_with_quality_gate.sh

DATASET_ID="${DATASET_ID:?set DATASET_ID}"
RAW_INPUT="${RAW_INPUT:?set RAW_INPUT}"

MANIFEST="${MANIFEST:-data/manifests/${DATASET_ID}.md}"
CONFIG_PATH="${CONFIG_PATH:-configs/base.toml}"
MODELSETS="${MODELSETS:-rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp}"
SEEDS="${SEEDS:-42,43,44}"
OUTPUT_TAG="${OUTPUT_TAG:-$(date +%F)_${DATASET_ID}}"
TORCH_DEVICE="${TORCH_DEVICE:-mps}"
AUTO_SELECT_COUNT="${AUTO_SELECT_COUNT:-3}"

PYTHONPATH=src python -m ais_risk.focus_seed_pipeline_cli \
  --manifest "${MANIFEST}" \
  --raw-input "${RAW_INPUT}" \
  --output-prefix "research_logs/${OUTPUT_TAG}_focus_seed_pipeline_auto_gate" \
  --output-root "outputs/${DATASET_ID}_focus_seed_pipeline_auto_gate_runs" \
  --config "${CONFIG_PATH}" \
  --auto-select-focus-mmsis \
  --auto-select-count "${AUTO_SELECT_COUNT}" \
  --auto-candidate-quality-gate-apply \
  --auto-candidate-quality-gate-strict \
  --seed-values "${SEEDS}" \
  --benchmark-modelsets "${MODELSETS}" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --validation-gate-min-seed-count 3 \
  --validation-gate-max-delta-case-f1-std 0.05 \
  --torch-device "${TORCH_DEVICE}"
