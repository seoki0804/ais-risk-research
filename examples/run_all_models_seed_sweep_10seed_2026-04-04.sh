#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed}"
SEEDS="${SEEDS:-41,42,43,44,45,46,47,48,49,50}"
REGIONS="${REGIONS:-houston,nola,seattle}"
ECE_GATE="${ECE_GATE:-0.10}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.all_models_seed_sweep_cli \
    --input-dir "${INPUT_DIR}" \
    --output-root "${OUTPUT_ROOT}" \
    --regions "${REGIONS}" \
    --seeds "${SEEDS}" \
    --split-strategy own_ship \
    --include-regional-cnn \
    --recommendation-max-ece-mean "${ECE_GATE}"
)

echo "summary_md=${OUTPUT_ROOT}/all_models_seed_sweep_summary.md"
echo "aggregate_csv=${OUTPUT_ROOT}/all_models_seed_sweep_aggregate.csv"
