#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECOMMENDATION_CSV="${RECOMMENDATION_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv}"
BASELINE_LEADERBOARD_CSV="${BASELINE_LEADERBOARD_CSV:-${ROOT}/outputs/2026-04-04_all_models_multiarea_expanded/all_models_multiarea_leaderboard.csv}"
OUT_OF_TIME_OUTPUT_ROOT="${OUT_OF_TIME_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_out_of_time_check_10seed}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed}"
DATASET_PREFIXES="${DATASET_PREFIXES:-houston,nola,seattle}"
THRESHOLD_GRID_STEP="${THRESHOLD_GRID_STEP:-0.01}"
MAX_OUT_OF_TIME_ECE="${MAX_OUT_OF_TIME_ECE:-0.10}"
MIN_OUT_OF_TIME_DELTA_F1="${MIN_OUT_OF_TIME_DELTA_F1:--0.05}"
MAX_IN_TIME_REGRESSION_FROM_BEST_F1="${MAX_IN_TIME_REGRESSION_FROM_BEST_F1:-0.02}"
INCLUDE_ORACLE_POLICY="${INCLUDE_ORACLE_POLICY:-1}"

(
  cd "${ROOT}"
  if [[ "${INCLUDE_ORACLE_POLICY}" == "1" ]]; then
    env PYTHONPATH=src python -m ais_risk.out_of_time_threshold_policy_compare_cli \
      --recommendation-csv "${RECOMMENDATION_CSV}" \
      --baseline-leaderboard-csv "${BASELINE_LEADERBOARD_CSV}" \
      --out-of-time-output-root "${OUT_OF_TIME_OUTPUT_ROOT}" \
      --output-prefix "${OUTPUT_PREFIX}" \
      --dataset-prefixes "${DATASET_PREFIXES}" \
      --threshold-grid-step "${THRESHOLD_GRID_STEP}" \
      --max-out-of-time-ece "${MAX_OUT_OF_TIME_ECE}" \
      --min-out-of-time-delta-f1 "${MIN_OUT_OF_TIME_DELTA_F1}" \
      --max-in-time-regression-from-best-f1 "${MAX_IN_TIME_REGRESSION_FROM_BEST_F1}"
  else
    env PYTHONPATH=src python -m ais_risk.out_of_time_threshold_policy_compare_cli \
      --recommendation-csv "${RECOMMENDATION_CSV}" \
      --baseline-leaderboard-csv "${BASELINE_LEADERBOARD_CSV}" \
      --out-of-time-output-root "${OUT_OF_TIME_OUTPUT_ROOT}" \
      --output-prefix "${OUTPUT_PREFIX}" \
      --dataset-prefixes "${DATASET_PREFIXES}" \
      --threshold-grid-step "${THRESHOLD_GRID_STEP}" \
      --max-out-of-time-ece "${MAX_OUT_OF_TIME_ECE}" \
      --min-out-of-time-delta-f1 "${MIN_OUT_OF_TIME_DELTA_F1}" \
      --max-in-time-regression-from-best-f1 "${MAX_IN_TIME_REGRESSION_FROM_BEST_F1}" \
      --disable-oracle-policy
  fi
)

echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
echo "detail_csv=${OUTPUT_PREFIX}_detail.csv"
echo "policy_summary_csv=${OUTPUT_PREFIX}_policy_summary.csv"
