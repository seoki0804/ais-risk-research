#!/usr/bin/env bash
set -euo pipefail

# Example wrapper for movement-ratio sensitivity on an existing own-ship candidate CSV.
# Usage:
#   INPUT=outputs/2026-03-14_noaa_nola_focus_candidates_pilot/own_ship_candidates_top20.csv \
#   OUTPUT_TAG=2026-03-14_noaa_nola_top20 \
#   ./examples/noaa_quality_gate_movement_sensitivity.sh

INPUT="${INPUT:?set INPUT}"
OUTPUT_TAG="${OUTPUT_TAG:?set OUTPUT_TAG}"
THRESHOLDS="${THRESHOLDS:-0.30 0.25 0.20}"

for threshold in ${THRESHOLDS}; do
  label="$(printf '%s' "${threshold}" | tr '.' '_')"
  PYTHONPATH=src python -m ais_risk.own_ship_quality_gate_cli \
    --input "${INPUT}" \
    --output-prefix "research_logs/${OUTPUT_TAG}_mr${label}" \
    --min-movement-ratio "${threshold}"
done
