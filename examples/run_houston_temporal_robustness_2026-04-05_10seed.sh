#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
BASELINE_AGGREGATE_CSV="${BASELINE_AGGREGATE_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv}"
BASELINE_RECOMMENDATION_CSV="${BASELINE_RECOMMENDATION_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv}"
TIMESTAMP_SWEEP_OUTPUT_ROOT="${TIMESTAMP_SWEEP_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-05_houston_timestamp_seed_sweep_10seed}"
TEMPORAL_ROBUST_OUTPUT_PREFIX="${TEMPORAL_ROBUST_OUTPUT_PREFIX:-${ROOT}/docs/temporal_robust_recommendation_2026-04-05_houston_10seed}"

(
  cd "${ROOT}"
  env PYTHONPATH=src python -m ais_risk.all_models_seed_sweep_cli \
    --input-dir "${INPUT_DIR}" \
    --output-root "${TIMESTAMP_SWEEP_OUTPUT_ROOT}" \
    --regions "houston" \
    --seeds "41,42,43,44,45,46,47,48,49,50" \
    --split-strategy "timestamp" \
    --include-regional-cnn \
    --cnn-losses "weighted_bce,focal" \
    --recommendation-f1-tolerance 0.01 \
    --recommendation-max-ece-mean 0.10 \
    --disable-auto-adjust-split

  env PYTHONPATH=src python -m ais_risk.temporal_robust_recommendation_cli \
    --baseline-aggregate-csv "${BASELINE_AGGREGATE_CSV}" \
    --out-of-time-aggregate-csv "${TIMESTAMP_SWEEP_OUTPUT_ROOT}/all_models_seed_sweep_aggregate.csv" \
    --baseline-recommendation-csv "${BASELINE_RECOMMENDATION_CSV}" \
    --dataset-prefixes "houston" \
    --output-prefix "${TEMPORAL_ROBUST_OUTPUT_PREFIX}" \
    --f1-tolerance 0.01 \
    --max-ece-mean 0.10 \
    --min-out-of-time-delta-f1 -0.05 \
    --delta-penalty-weight 1.0
)

echo "timestamp_sweep_summary=${TIMESTAMP_SWEEP_OUTPUT_ROOT}/all_models_seed_sweep_summary.md"
echo "temporal_robust_summary=${TEMPORAL_ROBUST_OUTPUT_PREFIX}.md"
