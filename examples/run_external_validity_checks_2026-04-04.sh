#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
RECOMMENDATION_CSV="${RECOMMENDATION_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_recommendation.csv}"
BASELINE_LEADERBOARD_CSV="${BASELINE_LEADERBOARD_CSV:-${ROOT}/outputs/2026-04-04_all_models_multiarea_expanded/all_models_multiarea_leaderboard.csv}"

OOT_OUTPUT_ROOT="${OOT_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_out_of_time_check}"
TRANSFER_OUTPUT_ROOT="${TRANSFER_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_transfer_check}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.out_of_time_eval_cli \
    --input-dir "${INPUT_DIR}" \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --baseline-leaderboard-csv "${BASELINE_LEADERBOARD_CSV}" \
    --output-root "${OOT_OUTPUT_ROOT}"
)

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.transfer_recommendation_eval_cli \
    --input-dir "${INPUT_DIR}" \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --output-root "${TRANSFER_OUTPUT_ROOT}"
)

(
  cd "${ROOT}"
  bash examples/export_github_results_bundle_2026-04-04_expanded.sh
)

echo "out_of_time_md=${OOT_OUTPUT_ROOT}/out_of_time_recommendation_check.md"
echo "transfer_md=${TRANSFER_OUTPUT_ROOT}/transfer_recommendation_check.md"
